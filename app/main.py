from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .config import Settings, get_settings
from .db import Base, create_db_engine, create_session_local
from .models import DailyRecord, Dog


templates = Jinja2Templates(directory="templates")


def parse_optional_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def validate_record_date(record_date: date) -> str | None:
    if record_date > date.today():
        return "記録日に未来の日付は使えません。"
    return None


def validate_weight(weight: str | None) -> tuple[float | None, str | None]:
    if not weight:
        return None, None
    try:
        parsed = float(weight)
    except ValueError:
        return None, "体重は数値で入力してください。"
    if parsed <= 0:
        return None, "体重は正の数で入力してください。"
    return parsed, None


def build_upload_url(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    return f"/uploads/{relative_path}"


async def save_upload(
    upload: UploadFile | None,
    settings: Settings,
    subdir: str,
) -> str | None:
    if not upload or not upload.filename:
        return None

    extension = Path(upload.filename).suffix.lower()
    if extension not in settings.allowed_image_extensions:
        raise HTTPException(status_code=400, detail="画像は jpg, jpeg, png, gif, webp のみ対応です。")

    data = await upload.read()
    if len(data) > settings.max_upload_size:
        raise HTTPException(status_code=400, detail="画像サイズは 5MB 以下にしてください。")

    upload_root = Path(settings.upload_dir)
    destination_dir = upload_root / subdir
    destination_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(8)}{extension}"
    destination = destination_dir / filename
    destination.write_bytes(data)
    return f"{subdir}/{filename}"


def delete_upload(relative_path: str | None, settings: Settings) -> None:
    if not relative_path:
        return
    file_path = Path(settings.upload_dir) / relative_path
    if file_path.exists() and file_path.is_file():
        file_path.unlink()


def redirect_with_message(url: str, message: str) -> RedirectResponse:
    separator = "&" if "?" in url else "?"
    return RedirectResponse(url=f"{url}{separator}message={quote(message)}", status_code=303)


def get_db(request: Request):
    session = request.app.state.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def render_template(
    request: Request,
    name: str,
    context: dict,
    status_code: int = 200,
) -> HTMLResponse:
    payload = {
        "request": request,
        "notice": request.query_params.get("message"),
        **context,
    }
    return templates.TemplateResponse(request, name, payload, status_code=status_code)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    app.state.engine = create_db_engine(settings)
    app.state.SessionLocal = create_session_local(app.state.engine)
    Base.metadata.create_all(bind=app.state.engine)
    yield
    app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Dog Growth Journal", lifespan=lifespan)
    app.state.settings = settings or get_settings()
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.mount(
        "/uploads",
        StaticFiles(directory=app.state.settings.upload_dir, check_dir=False),
        name="uploads",
    )

    def validate_record_form(
        db: Session,
        dog_id: str,
        record_date: str,
        weight: str,
    ) -> tuple[list[str], Dog | None, date | None, float | None]:
        errors: list[str] = []
        dog = None
        parsed_date = None
        parsed_weight = None

        if not dog_id:
            errors.append("対象の犬を選択してください。")
        else:
            try:
                dog = db.get(Dog, int(dog_id))
            except ValueError:
                dog = None
            if not dog:
                errors.append("対象の犬が見つかりません。")

        if not record_date:
            errors.append("記録日は必須です。")
        else:
            try:
                parsed_date = date.fromisoformat(record_date)
                error = validate_record_date(parsed_date)
                if error:
                    errors.append(error)
            except ValueError:
                errors.append("記録日は YYYY-MM-DD 形式で入力してください。")

        parsed_weight, weight_error = validate_weight(weight)
        if weight_error:
            errors.append(weight_error)

        return errors, dog, parsed_date, parsed_weight

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, db: Session = Depends(get_db)):
        dogs = db.scalars(
            select(Dog).options(selectinload(Dog.records)).order_by(Dog.name.asc())
        ).all()
        recent_records = db.scalars(
            select(DailyRecord)
            .options(selectinload(DailyRecord.dog))
            .order_by(DailyRecord.record_date.desc(), DailyRecord.created_at.desc())
            .limit(10)
        ).all()
        today = date.today()
        week_start = today - timedelta(days=6)
        total_records = db.scalar(select(func.count(DailyRecord.id))) or 0
        weekly_records = db.scalar(
            select(func.count(DailyRecord.id)).where(DailyRecord.record_date >= week_start)
        ) or 0
        dog_summaries = []
        for dog in dogs:
            latest_record = max(dog.records, key=lambda item: item.record_date) if dog.records else None
            dog_summaries.append(
                {
                    "dog": dog,
                    "record_count": len(dog.records),
                    "latest_record": latest_record,
                }
            )
        return render_template(
            request,
            "home.html",
            {
                "dogs": dogs,
                "recent_records": recent_records,
                "selected_dog": None,
                "total_records": total_records,
                "weekly_records": weekly_records,
                "dog_summaries": dog_summaries,
            },
        )

    @app.get("/healthz")
    def healthcheck():
        return {"status": "ok"}

    @app.get("/dogs", response_class=HTMLResponse)
    def dogs_page(request: Request, db: Session = Depends(get_db)):
        dogs = db.scalars(select(Dog).order_by(Dog.name.asc())).all()
        return render_template(
            request,
            "dogs.html",
            {"dogs": dogs, "errors": [], "form_data": {}},
        )

    @app.post("/dogs", response_class=HTMLResponse)
    async def create_dog(
        request: Request,
        name: str = Form(...),
        birth_date: str = Form(""),
        breed: str = Form(""),
        sex: str = Form(""),
        notes: str = Form(""),
        profile_image: UploadFile | None = File(default=None),
        db: Session = Depends(get_db),
    ):
        errors: list[str] = []
        form_data = {
            "name": name,
            "birth_date": birth_date,
            "breed": breed,
            "sex": sex,
            "notes": notes,
        }
        if not name.strip():
            errors.append("犬名は必須です。")

        parsed_birth_date = None
        if birth_date:
            try:
                parsed_birth_date = parse_optional_date(birth_date)
            except ValueError:
                errors.append("生年月日は YYYY-MM-DD 形式で入力してください。")

        image_path = None
        if not errors:
            try:
                image_path = await save_upload(profile_image, request.app.state.settings, "dogs")
            except HTTPException as exc:
                errors.append(exc.detail)

        if errors:
            dogs = db.scalars(select(Dog).order_by(Dog.name.asc())).all()
            return render_template(
                request,
                "dogs.html",
                {"dogs": dogs, "errors": errors, "form_data": form_data},
                status_code=400,
            )

        dog = Dog(
            name=name.strip(),
            birth_date=parsed_birth_date,
            breed=breed.strip() or None,
            sex=sex.strip() or None,
            notes=notes.strip() or None,
            profile_image=image_path,
        )
        db.add(dog)
        db.commit()
        return redirect_with_message(f"/dogs/{dog.id}", f"{dog.name} を登録しました。")

    @app.get("/dogs/{dog_id}", response_class=HTMLResponse)
    def dog_detail(request: Request, dog_id: int, db: Session = Depends(get_db)):
        dog = db.scalar(
            select(Dog).options(selectinload(Dog.records)).where(Dog.id == dog_id)
        )
        if not dog:
            raise HTTPException(status_code=404, detail="Dog not found")
        latest_record = max(dog.records, key=lambda item: item.record_date) if dog.records else None
        return render_template(
            request,
            "dog_detail.html",
            {
                "dog": dog,
                "latest_record": latest_record,
                "record_errors": [],
                "record_form_data": {"dog_id": dog_id},
            },
        )

    @app.get("/dogs/{dog_id}/edit", response_class=HTMLResponse)
    def edit_dog_page(request: Request, dog_id: int, db: Session = Depends(get_db)):
        dog = db.get(Dog, dog_id)
        if not dog:
            raise HTTPException(status_code=404, detail="Dog not found")
        return render_template(
            request,
            "dog_edit.html",
            {"dog": dog, "errors": [], "form_data": {}},
        )

    @app.post("/dogs/{dog_id}/edit", response_class=HTMLResponse)
    async def edit_dog(
        request: Request,
        dog_id: int,
        name: str = Form(...),
        birth_date: str = Form(""),
        breed: str = Form(""),
        sex: str = Form(""),
        notes: str = Form(""),
        remove_profile_image: str | None = Form(default=None),
        profile_image: UploadFile | None = File(default=None),
        db: Session = Depends(get_db),
    ):
        dog = db.get(Dog, dog_id)
        if not dog:
            raise HTTPException(status_code=404, detail="Dog not found")

        errors: list[str] = []
        form_data = {
            "name": name,
            "birth_date": birth_date,
            "breed": breed,
            "sex": sex,
            "notes": notes,
        }
        if not name.strip():
            errors.append("犬名は必須です。")

        parsed_birth_date = None
        if birth_date:
            try:
                parsed_birth_date = parse_optional_date(birth_date)
            except ValueError:
                errors.append("生年月日は YYYY-MM-DD 形式で入力してください。")

        if not errors and profile_image and profile_image.filename:
            old_image = dog.profile_image
            try:
                dog.profile_image = await save_upload(profile_image, request.app.state.settings, "dogs")
                delete_upload(old_image, request.app.state.settings)
            except HTTPException as exc:
                errors.append(exc.detail)
        elif not errors and remove_profile_image and dog.profile_image:
            delete_upload(dog.profile_image, request.app.state.settings)
            dog.profile_image = None

        if errors:
            return render_template(
                request,
                "dog_edit.html",
                {"dog": dog, "errors": errors, "form_data": form_data},
                status_code=400,
            )

        dog.name = name.strip()
        dog.birth_date = parsed_birth_date
        dog.breed = breed.strip() or None
        dog.sex = sex.strip() or None
        dog.notes = notes.strip() or None
        db.commit()
        return redirect_with_message(f"/dogs/{dog.id}", f"{dog.name} のプロフィールを更新しました。")

    @app.post("/dogs/{dog_id}/delete")
    def delete_dog(request: Request, dog_id: int, db: Session = Depends(get_db)):
        dog = db.scalar(select(Dog).options(selectinload(Dog.records)).where(Dog.id == dog_id))
        if not dog:
            raise HTTPException(status_code=404, detail="Dog not found")

        dog_name = dog.name
        upload_paths = [dog.profile_image, *[record.photo_path for record in dog.records]]
        db.delete(dog)
        db.commit()

        for upload_path in upload_paths:
            delete_upload(upload_path, request.app.state.settings)

        return redirect_with_message("/dogs", f"{dog_name} を削除しました。")

    @app.get("/records", response_class=HTMLResponse)
    def records_page(request: Request, dog_id: int | None = None, db: Session = Depends(get_db)):
        dogs = db.scalars(select(Dog).order_by(Dog.name.asc())).all()
        query = select(DailyRecord).options(selectinload(DailyRecord.dog)).order_by(
            DailyRecord.record_date.desc(), DailyRecord.created_at.desc()
        )
        selected_dog = None
        if dog_id:
            selected_dog = db.get(Dog, dog_id)
            if selected_dog:
                query = query.where(DailyRecord.dog_id == dog_id)
        records = db.scalars(query).all()
        return render_template(
            request,
            "records.html",
            {
                "dogs": dogs,
                "records": records,
                "selected_dog": selected_dog,
                "errors": [],
                "form_data": {"dog_id": str(dog_id) if dog_id else ""},
            },
        )

    @app.post("/records", response_class=HTMLResponse)
    async def create_record(
        request: Request,
        dog_id: str = Form(...),
        record_date: str = Form(...),
        weight: str = Form(""),
        food_notes: str = Form(""),
        walk_notes: str = Form(""),
        health_notes: str = Form(""),
        photo: UploadFile | None = File(default=None),
        db: Session = Depends(get_db),
    ):
        errors, dog, parsed_date, parsed_weight = validate_record_form(db, dog_id, record_date, weight)
        form_data = {
            "dog_id": dog_id,
            "record_date": record_date,
            "weight": weight,
            "food_notes": food_notes,
            "walk_notes": walk_notes,
            "health_notes": health_notes,
        }
        photo_path = None
        if not errors:
            try:
                photo_path = await save_upload(photo, request.app.state.settings, "records")
            except HTTPException as exc:
                errors.append(exc.detail)

        if errors:
            dogs = db.scalars(select(Dog).order_by(Dog.name.asc())).all()
            records = db.scalars(
                select(DailyRecord)
                .options(selectinload(DailyRecord.dog))
                .order_by(DailyRecord.record_date.desc(), DailyRecord.created_at.desc())
            ).all()
            return render_template(
                request,
                "records.html",
                {
                    "dogs": dogs,
                    "records": records,
                    "selected_dog": dog,
                    "errors": errors,
                    "form_data": form_data,
                },
                status_code=400,
            )

        record = DailyRecord(
            dog_id=dog.id,
            record_date=parsed_date,
            weight=parsed_weight,
            food_notes=food_notes.strip() or None,
            walk_notes=walk_notes.strip() or None,
            health_notes=health_notes.strip() or None,
            photo_path=photo_path,
        )
        db.add(record)
        db.commit()
        return redirect_with_message(f"/dogs/{dog.id}", f"{dog.name} の記録を追加しました。")

    @app.get("/records/{record_id}/edit", response_class=HTMLResponse)
    def edit_record_page(request: Request, record_id: int, db: Session = Depends(get_db)):
        record = db.scalar(
            select(DailyRecord).options(selectinload(DailyRecord.dog)).where(DailyRecord.id == record_id)
        )
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        dogs = db.scalars(select(Dog).order_by(Dog.name.asc())).all()
        return render_template(
            request,
            "record_edit.html",
            {"record": record, "dogs": dogs, "errors": [], "form_data": {}},
        )

    @app.post("/records/{record_id}/edit", response_class=HTMLResponse)
    async def edit_record(
        request: Request,
        record_id: int,
        dog_id: str = Form(...),
        record_date: str = Form(...),
        weight: str = Form(""),
        food_notes: str = Form(""),
        walk_notes: str = Form(""),
        health_notes: str = Form(""),
        remove_photo: str | None = Form(default=None),
        photo: UploadFile | None = File(default=None),
        db: Session = Depends(get_db),
    ):
        record = db.get(DailyRecord, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        errors, dog, parsed_date, parsed_weight = validate_record_form(db, dog_id, record_date, weight)
        form_data = {
            "dog_id": dog_id,
            "record_date": record_date,
            "weight": weight,
            "food_notes": food_notes,
            "walk_notes": walk_notes,
            "health_notes": health_notes,
        }
        if not errors and photo and photo.filename:
            old_photo = record.photo_path
            try:
                record.photo_path = await save_upload(photo, request.app.state.settings, "records")
                delete_upload(old_photo, request.app.state.settings)
            except HTTPException as exc:
                errors.append(exc.detail)
        elif not errors and remove_photo and record.photo_path:
            delete_upload(record.photo_path, request.app.state.settings)
            record.photo_path = None

        if errors:
            dogs = db.scalars(select(Dog).order_by(Dog.name.asc())).all()
            hydrated_record = db.scalar(
                select(DailyRecord).options(selectinload(DailyRecord.dog)).where(DailyRecord.id == record_id)
            )
            return render_template(
                request,
                "record_edit.html",
                {"record": hydrated_record, "dogs": dogs, "errors": errors, "form_data": form_data},
                status_code=400,
            )

        record.dog_id = dog.id
        record.record_date = parsed_date
        record.weight = parsed_weight
        record.food_notes = food_notes.strip() or None
        record.walk_notes = walk_notes.strip() or None
        record.health_notes = health_notes.strip() or None
        db.commit()
        return redirect_with_message(f"/dogs/{dog.id}", f"{dog.name} の記録を更新しました。")

    @app.post("/records/{record_id}/delete")
    def delete_record(request: Request, record_id: int, db: Session = Depends(get_db)):
        record = db.get(DailyRecord, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        dog_id = record.dog_id
        dog_name = record.dog.name if record.dog else "記録"
        photo_path = record.photo_path
        db.delete(record)
        db.commit()
        delete_upload(photo_path, request.app.state.settings)
        return redirect_with_message(f"/dogs/{dog_id}", f"{dog_name} の記録を削除しました。")

    @app.get("/api/dogs")
    def api_list_dogs(db: Session = Depends(get_db)):
        dogs = db.scalars(select(Dog).order_by(Dog.name.asc())).all()
        return [
            {
                "id": dog.id,
                "name": dog.name,
                "birth_date": dog.birth_date.isoformat() if dog.birth_date else None,
                "breed": dog.breed,
                "sex": dog.sex,
                "notes": dog.notes,
                "profile_image_url": build_upload_url(dog.profile_image),
            }
            for dog in dogs
        ]

    @app.post("/api/dogs", status_code=201)
    async def api_create_dog(
        request: Request,
        name: str = Form(...),
        birth_date: str = Form(""),
        breed: str = Form(""),
        sex: str = Form(""),
        notes: str = Form(""),
        profile_image: UploadFile | None = File(default=None),
        db: Session = Depends(get_db),
    ):
        if not name.strip():
            raise HTTPException(status_code=400, detail="犬名は必須です。")
        try:
            parsed_birth_date = parse_optional_date(birth_date) if birth_date else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="生年月日は YYYY-MM-DD 形式で入力してください。") from exc
        image_path = await save_upload(profile_image, request.app.state.settings, "dogs")
        dog = Dog(
            name=name.strip(),
            birth_date=parsed_birth_date,
            breed=breed.strip() or None,
            sex=sex.strip() or None,
            notes=notes.strip() or None,
            profile_image=image_path,
        )
        db.add(dog)
        db.commit()
        db.refresh(dog)
        return {"id": dog.id, "name": dog.name}

    @app.delete("/api/dogs/{dog_id}", status_code=204)
    def api_delete_dog(dog_id: int, request: Request, db: Session = Depends(get_db)):
        dog = db.scalar(select(Dog).options(selectinload(Dog.records)).where(Dog.id == dog_id))
        if not dog:
            raise HTTPException(status_code=404, detail="Dog not found")

        upload_paths = [dog.profile_image, *[record.photo_path for record in dog.records]]
        db.delete(dog)
        db.commit()
        for upload_path in upload_paths:
            delete_upload(upload_path, request.app.state.settings)
        return Response(status_code=204)

    @app.post("/api/records", status_code=201)
    async def api_create_record(
        request: Request,
        dog_id: str = Form(...),
        record_date: str = Form(...),
        weight: str = Form(""),
        food_notes: str = Form(""),
        walk_notes: str = Form(""),
        health_notes: str = Form(""),
        photo: UploadFile | None = File(default=None),
        db: Session = Depends(get_db),
    ):
        errors, dog, parsed_date, parsed_weight = validate_record_form(db, dog_id, record_date, weight)
        if errors:
            raise HTTPException(status_code=400, detail=errors)
        photo_path = await save_upload(photo, request.app.state.settings, "records")
        record = DailyRecord(
            dog_id=dog.id,
            record_date=parsed_date,
            weight=parsed_weight,
            food_notes=food_notes.strip() or None,
            walk_notes=walk_notes.strip() or None,
            health_notes=health_notes.strip() or None,
            photo_path=photo_path,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"id": record.id, "dog_id": record.dog_id, "record_date": record.record_date.isoformat()}

    @app.delete("/api/records/{record_id}", status_code=204)
    def api_delete_record(record_id: int, request: Request, db: Session = Depends(get_db)):
        record = db.get(DailyRecord, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        photo_path = record.photo_path
        db.delete(record)
        db.commit()
        delete_upload(photo_path, request.app.state.settings)
        return Response(status_code=204)

    @app.post("/api/uploads", status_code=201)
    async def api_upload_file(
        request: Request,
        photo: UploadFile = File(...),
    ):
        path = await save_upload(photo, request.app.state.settings, "records")
        return {"path": path, "url": build_upload_url(path)}

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        if exc.status_code == 404:
            return render_template(request, "not_found.html", {"message": "ページが見つかりません。"}, status_code=404)
        return render_template(
            request,
            "error.html",
            {"message": exc.detail if isinstance(exc.detail, str) else "入力エラーが発生しました。"},
            status_code=exc.status_code,
        )

    return app


app = create_app()
