def test_create_member_requires_membership_number_and_name(client, make_headers, librarian):
    resp = client.post("/api/members", json={"fullName": "No Number"}, headers=make_headers(librarian))
    assert resp.status_code == 400


def test_duplicate_membership_number_rejected(client, make_headers, librarian, sample_member):
    resp = client.post(
        "/api/members",
        json={"membershipNumber": sample_member.membership_number, "fullName": "Someone Else"},
        headers=make_headers(librarian),
    )
    assert resp.status_code == 409


def test_get_member_includes_loan_history(client, make_headers, librarian, sample_book, sample_member):
    client.post(
        "/api/circulation/issue",
        json={"bookId": sample_book.id, "memberId": sample_member.id},
        headers=make_headers(librarian),
    )
    resp = client.get(f"/api/members/{sample_member.id}", headers=make_headers(librarian))
    assert resp.status_code == 200
    assert len(resp.get_json()["loans"]) == 1


def test_update_member_status(client, make_headers, librarian, sample_member):
    resp = client.put(
        f"/api/members/{sample_member.id}", json={"status": "suspended"}, headers=make_headers(librarian)
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "suspended"


def test_update_member_rejects_invalid_status(client, make_headers, librarian, sample_member):
    resp = client.put(
        f"/api/members/{sample_member.id}", json={"status": "not-a-real-status"}, headers=make_headers(librarian)
    )
    # Invalid status is silently ignored rather than erroring -- status stays unchanged.
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "active"


def test_delete_member_with_active_loan_fails(client, make_headers, librarian, sample_book, sample_member):
    client.post(
        "/api/circulation/issue",
        json={"bookId": sample_book.id, "memberId": sample_member.id},
        headers=make_headers(librarian),
    )
    resp = client.delete(f"/api/members/{sample_member.id}", headers=make_headers(librarian))
    assert resp.status_code == 400


def test_delete_member_without_loans_archives_not_hard_deletes(client, make_headers, librarian, sample_member):
    resp = client.delete(f"/api/members/{sample_member.id}", headers=make_headers(librarian))
    assert resp.status_code == 200

    # Archived members are excluded from the default list...
    listed = client.get("/api/members", headers=make_headers(librarian)).get_json()
    assert sample_member.id not in [m["id"] for m in listed]

    # ...but still retrievable directly (loan history preserved).
    fetched = client.get(f"/api/members/{sample_member.id}", headers=make_headers(librarian))
    assert fetched.status_code == 200
    assert fetched.get_json()["status"] == "archived"
