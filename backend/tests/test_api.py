"""The paths where a regression loses user data or opens the PC to the web."""

from __future__ import annotations


def _first_page(client):
    profile = next(p for p in client.get("/api/profiles").json() if p["active"])
    return client.get(f"/api/profiles/{profile['id']}/pages").json()[0]


def _template(client):
    return client.get("/api/actions").json()[0]


def _tile_at(client, page_id, row, col):
    slots = client.get(f"/api/pages/{page_id}/tiles").json()
    return next(s["tile"] for s in slots if s["row"] == row and s["col"] == col)


# -- origin guard ------------------------------------------------------------


def test_cross_site_request_is_refused(client):
    response = client.post(
        "/api/profiles", json={"name": "x"}, headers={"origin": "https://evil.example"}
    )
    assert response.status_code == 403


def test_rebound_hostname_is_refused(client):
    # DNS rebinding: the attacker's domain resolves to us, and Origin matches Host.
    headers = {"host": "evil.example:8770", "origin": "http://evil.example:8770"}
    assert client.get("/api/profiles", headers=headers).status_code == 403


def test_same_origin_and_lan_requests_pass(client):
    assert client.get("/api/health", headers={"origin": "http://127.0.0.1:8770"}).status_code == 200
    lan = {"host": "192.168.1.20:8770", "origin": "http://192.168.1.20:8770"}
    assert client.get("/api/health", headers=lan).status_code == 200


# -- tiles -------------------------------------------------------------------


def test_moving_onto_an_occupied_slot_swaps(client):
    page = _first_page(client)
    a = _tile_at(client, page["id"], 0, 0)
    b = _tile_at(client, page["id"], 0, 1)
    assert a and b, "the seed places tiles on the first row"

    assert client.patch(f"/api/tiles/{a['id']}", json={"row": 0, "col": 1}).status_code == 200

    assert _tile_at(client, page["id"], 0, 1)["id"] == a["id"]
    assert _tile_at(client, page["id"], 0, 0)["id"] == b["id"]


def test_each_tile_gets_its_own_action_copy(client):
    page = _first_page(client)
    template = _template(client)
    first = client.post(
        "/api/tiles", json={"page_id": page["id"], "row": 2, "col": 0, "action_id": template["id"]}
    ).json()
    second = client.post(
        "/api/tiles", json={"page_id": page["id"], "row": 2, "col": 1, "action_id": template["id"]}
    ).json()

    ids = {first["action_id"], second["action_id"], template["id"]}
    assert len(ids) == 3


def test_undoing_a_clear_reuses_the_tiles_copy(client):
    page = _first_page(client)
    tile = _tile_at(client, page["id"], 0, 0)
    client.delete(f"/api/tiles/{tile['id']}")

    restored = client.post(
        "/api/tiles",
        json={"page_id": page["id"], "row": 0, "col": 0, "action_id": tile["action_id"]},
    ).json()
    assert restored["action_id"] == tile["action_id"]


def test_null_position_leaves_the_tile_in_place(client):
    page = _first_page(client)
    tile = _tile_at(client, page["id"], 0, 0)
    response = client.patch(f"/api/tiles/{tile['id']}", json={"row": None, "custom_label": "Hi"})
    assert response.status_code == 200
    assert (response.json()["row"], response.json()["col"]) == (0, 0)


# -- pages -------------------------------------------------------------------


def test_page_geometry_is_validated_on_create(client):
    page = _first_page(client)
    body = {"profile_id": page["profile_id"], "name": "Big", "color": "pc"}
    assert client.post("/api/pages", json={**body, "rows": 6, "cols": 6}).status_code == 201
    assert client.post("/api/pages", json={**body, "rows": 50, "cols": 5}).status_code == 422


# -- boot-time cleanup -------------------------------------------------------


def test_restart_keeps_a_users_variant_of_a_seeded_action(client):
    from app.seed import seed

    original = _template(client)
    variant = client.post(
        "/api/actions",
        json={
            "category_id": original["category_id"],
            "label": original["label"] + " (mine)",
            "icon": original["icon"],
            "type": original["type"],
            "endpoint": original["endpoint"],
            "params": original["params"],
        },
    ).json()

    seed()  # what every app start runs on an existing database

    ids = {a["id"] for a in client.get("/api/actions").json()}
    assert {original["id"], variant["id"]} <= ids
