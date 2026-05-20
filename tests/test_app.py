from io import BytesIO
from pathlib import Path


def test_setup_and_login_flow(raw_client):
    setup_page = raw_client.get("/", follow_redirects=True)
    assert setup_page.status_code == 200
    assert "最初のログインアカウントを作成" in setup_page.text

    created = raw_client.post(
        "/setup",
        data={
            "email": "owner@example.com",
            "password": "verysecurepassword",
            "password_confirm": "verysecurepassword",
        },
        follow_redirects=True,
    )
    assert created.status_code == 200
    assert "ログイン用アカウントを作成しました" in created.text

    logout = raw_client.post("/logout", follow_redirects=True)
    assert logout.status_code == 200
    assert "ログアウトしました" in logout.text

    failed = raw_client.post(
        "/login",
        data={"email": "owner@example.com", "password": "wrongpass123"},
        follow_redirects=True,
    )
    assert failed.status_code == 400
    assert "メールアドレスまたはパスワードが違います" in failed.text

    login = raw_client.post(
        "/login",
        data={"email": "owner@example.com", "password": "verysecurepassword"},
        follow_redirects=True,
    )
    assert login.status_code == 200
    assert "ログインしました" in login.text


def test_create_multiple_dogs_and_list_in_api(client):
    response = client.post(
        "/dogs",
        data={
            "name": "Mugi",
            "birth_date": "2023-01-01",
            "breed": "Shiba",
            "sex": "オス",
            "notes": "元気",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "message=" in response.headers["location"]

    response = client.post(
        "/api/dogs",
        data={"name": "Sora", "breed": "Toy Poodle"},
    )
    assert response.status_code == 201

    response = client.get("/api/dogs")
    assert response.status_code == 200
    names = [dog["name"] for dog in response.json()]
    assert names == ["Mugi", "Sora"]


def test_requires_login_after_setup(raw_client):
    raw_client.post(
        "/setup",
        data={
            "email": "owner@example.com",
            "password": "verysecurepassword",
            "password_confirm": "verysecurepassword",
        },
        follow_redirects=True,
    )
    raw_client.post("/logout", follow_redirects=True)

    page = raw_client.get("/dogs", follow_redirects=False)
    assert page.status_code == 303
    assert page.headers["location"] == "/login"

    api_response = raw_client.get("/api/dogs")
    assert api_response.status_code == 401


def test_create_record_for_specific_dog_and_filter_records(client):
    first = client.post("/api/dogs", data={"name": "Mugi"})
    second = client.post("/api/dogs", data={"name": "Sora"})
    first_id = first.json()["id"]
    second_id = second.json()["id"]

    response = client.post(
        "/api/records",
        data={
            "dog_id": str(first_id),
            "record_date": "2026-05-01",
            "weight": "8.6",
            "food_notes": "完食",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/api/records",
        data={
            "dog_id": str(second_id),
            "record_date": "2026-05-02",
            "weight": "4.2",
            "food_notes": "少なめ",
        },
    )
    assert response.status_code == 201

    page = client.get(f"/records?dog_id={first_id}")
    assert page.status_code == 200
    assert "Mugi" in page.text
    assert "8.6kg" in page.text
    assert "4.2kg" not in page.text


def test_reject_invalid_record_inputs(client):
    dog = client.post("/api/dogs", data={"name": "Mugi"}).json()
    response = client.post(
        "/api/records",
        data={
            "dog_id": str(dog["id"]),
            "record_date": "3026-05-01",
            "weight": "-1",
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "未来の日付" in detail[0]
    assert "正の数" in detail[1]


def test_upload_validation_and_success(client):
    dog = client.post("/api/dogs", data={"name": "Mugi"}).json()

    bad_upload = client.post(
        "/api/uploads",
        files={"photo": ("note.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert bad_upload.status_code == 400

    good_upload = client.post(
        "/api/records",
        data={
            "dog_id": str(dog["id"]),
            "record_date": "2026-05-03",
        },
        files={"photo": ("photo.png", BytesIO(b"fakepng"), "image/png")},
    )
    assert good_upload.status_code == 201


def test_delete_record_removes_photo_and_keeps_dog(client):
    dog = client.post("/api/dogs", data={"name": "Mugi"}).json()
    created = client.post(
        "/api/records",
        data={
            "dog_id": str(dog["id"]),
            "record_date": "2026-05-03",
        },
        files={"photo": ("photo.png", BytesIO(b"fakepng"), "image/png")},
    ).json()

    delete_response = client.delete(f"/api/records/{created['id']}")
    assert delete_response.status_code == 204

    page = client.get(f"/dogs/{dog['id']}")
    assert page.status_code == 200
    assert "この犬の記録はまだありません。" in page.text


def test_delete_dog_removes_records_and_redirects_home(client):
    dog = client.post("/api/dogs", data={"name": "Mugi"}).json()
    client.post(
        "/api/records",
        data={
            "dog_id": str(dog["id"]),
            "record_date": "2026-05-04",
            "weight": "7.8",
        },
    )

    delete_response = client.delete(f"/api/dogs/{dog['id']}")
    assert delete_response.status_code == 204

    dogs = client.get("/api/dogs")
    assert dogs.status_code == 200
    assert dogs.json() == []


def test_edit_dog_can_remove_profile_image(client):
    response = client.post(
        "/api/dogs",
        data={"name": "Mugi"},
        files={"profile_image": ("dog.png", BytesIO(b"fakepng"), "image/png")},
    )
    dog_id = response.json()["id"]
    upload_dir = Path(client.app.state.settings.upload_dir) / "dogs"
    assert any(upload_dir.iterdir())

    update = client.post(
        f"/dogs/{dog_id}/edit",
        data={
            "name": "Mugi",
            "birth_date": "",
            "breed": "",
            "sex": "",
            "notes": "",
            "remove_profile_image": "1",
        },
        follow_redirects=True,
    )
    assert update.status_code == 200
    assert "プロフィールを更新しました" in update.text
    assert not any(upload_dir.iterdir())


def test_edit_record_can_remove_photo(client):
    dog = client.post("/api/dogs", data={"name": "Mugi"}).json()
    created = client.post(
        "/api/records",
        data={
            "dog_id": str(dog["id"]),
            "record_date": "2026-05-05",
        },
        files={"photo": ("record.png", BytesIO(b"fakepng"), "image/png")},
    ).json()
    upload_dir = Path(client.app.state.settings.upload_dir) / "records"
    assert any(upload_dir.iterdir())

    update = client.post(
        f"/records/{created['id']}/edit",
        data={
            "dog_id": str(dog["id"]),
            "record_date": "2026-05-05",
            "weight": "",
            "food_notes": "",
            "walk_notes": "",
            "health_notes": "",
            "remove_photo": "1",
        },
        follow_redirects=True,
    )
    assert update.status_code == 200
    assert "記録を更新しました" in update.text
    assert not any(upload_dir.iterdir())


def test_home_shows_summary_stats(client):
    dog = client.post("/api/dogs", data={"name": "Mugi"}).json()
    client.post(
        "/api/records",
        data={
            "dog_id": str(dog["id"]),
            "record_date": "2026-05-05",
            "weight": "8.1",
        },
    )
    page = client.get("/")
    assert page.status_code == 200
    assert "これまでの記録数" in page.text
    assert "最新 8.1kg" in page.text
