"""
RBAC matrix: for each permission-gated action, confirm every role gets the
outcome app/permissions.py says it should. This is what stops "broken
access control" -- a route accidentally checking the wrong permission
string, or a role gaining access it shouldn't have.
"""
import pytest


@pytest.mark.parametrize("role_fixture,expected_status", [
    ("super_admin", 201),
    ("librarian", 201),
    ("staff", 403),
])
def test_only_librarian_and_above_can_create_books(client, make_headers, request, role_fixture, expected_status):
    user = request.getfixturevalue(role_fixture)
    resp = client.post(
        "/api/books", json={"title": "New Book", "author": "Someone"}, headers=make_headers(user)
    )
    assert resp.status_code == expected_status


@pytest.mark.parametrize("role_fixture,expected_status", [
    ("super_admin", 200),
    ("librarian", 200),
    ("staff", 403),
])
def test_only_librarian_and_above_can_delete_books(
    client, make_headers, request, sample_book, role_fixture, expected_status
):
    user = request.getfixturevalue(role_fixture)
    resp = client.delete(f"/api/books/{sample_book.id}", headers=make_headers(user))
    assert resp.status_code == expected_status


@pytest.mark.parametrize("role_fixture", ["super_admin", "librarian", "staff"])
def test_all_staff_roles_can_read_members(client, make_headers, request, role_fixture):
    user = request.getfixturevalue(role_fixture)
    resp = client.get("/api/members", headers=make_headers(user))
    assert resp.status_code == 200


@pytest.mark.parametrize("role_fixture,expected_status", [
    ("super_admin", 201),
    ("librarian", 201),
    ("staff", 403),
])
def test_only_librarian_and_above_can_create_members(client, make_headers, request, role_fixture, expected_status):
    user = request.getfixturevalue(role_fixture)
    resp = client.post(
        "/api/members",
        json={"membershipNumber": f"M-{role_fixture}", "fullName": "Test Patron"},
        headers=make_headers(user),
    )
    assert resp.status_code == expected_status


@pytest.mark.parametrize("role_fixture", ["super_admin", "librarian", "staff"])
def test_all_staff_roles_can_issue_books(client, make_headers, request, role_fixture, sample_book, sample_member):
    user = request.getfixturevalue(role_fixture)
    resp = client.post(
        "/api/circulation/issue",
        json={"bookId": sample_book.id, "memberId": sample_member.id},
        headers=make_headers(user),
    )
    assert resp.status_code == 201


def test_self_registered_member_role_has_no_staff_permissions(client, make_headers, member_role_user):
    resp = client.get("/api/members", headers=make_headers(member_role_user))
    assert resp.status_code == 403

    resp = client.post(
        "/api/books", json={"title": "X", "author": "Y"}, headers=make_headers(member_role_user)
    )
    assert resp.status_code == 403


def test_unauthenticated_requests_are_401_not_403(client):
    """403 vs 401 matters: 401 means 'log in', 403 means 'you're logged in
    but not allowed'. permission_required must check auth before permission."""
    resp = client.post("/api/books", json={"title": "X", "author": "Y"})
    assert resp.status_code == 401
