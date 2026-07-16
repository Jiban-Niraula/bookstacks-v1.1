def test_self_service_borrow_and_return(client, make_headers, member_role_user, sample_book):
    resp = client.post(f"/api/books/{sample_book.id}/borrow", headers=make_headers(member_role_user))
    assert resp.status_code == 200
    assert resp.get_json()["availableCopies"] == sample_book.total_copies - 1

    my_loans = client.get("/api/my/loans", headers=make_headers(member_role_user)).get_json()
    assert len(my_loans) == 1
    assert my_loans[0]["overdue"] is False

    resp = client.post(f"/api/books/{sample_book.id}/return", headers=make_headers(member_role_user))
    assert resp.status_code == 200
    assert resp.get_json()["availableCopies"] == sample_book.total_copies


def test_cannot_double_borrow_same_book(client, make_headers, member_role_user, sample_book):
    client.post(f"/api/books/{sample_book.id}/borrow", headers=make_headers(member_role_user))
    resp = client.post(f"/api/books/{sample_book.id}/borrow", headers=make_headers(member_role_user))
    assert resp.status_code == 400


def test_borrow_fails_when_no_copies_available(client, make_headers, db):
    from app.models import Book
    book = Book(title="Single Copy", author="A", total_copies=1)
    db.session.add(book)
    db.session.commit()

    from tests.conftest import _make_user
    user_a = _make_user(db, "borrower_a", "member")
    user_b = _make_user(db, "borrower_b", "member")

    client.post(f"/api/books/{book.id}/borrow", headers=make_headers(user_a))
    resp = client.post(f"/api/books/{book.id}/borrow", headers=make_headers(user_b))
    assert resp.status_code == 400


def test_self_service_user_cannot_return_someone_elses_loan(client, make_headers, db, sample_book):
    from tests.conftest import _make_user
    user_a = _make_user(db, "owner", "member")
    user_b = _make_user(db, "not_owner", "member")

    client.post(f"/api/books/{sample_book.id}/borrow", headers=make_headers(user_a))
    resp = client.post(f"/api/books/{sample_book.id}/return", headers=make_headers(user_b))
    assert resp.status_code == 400


def test_staff_can_return_any_users_loan(client, make_headers, db, staff, sample_book):
    from tests.conftest import _make_user
    patron = _make_user(db, "patron_owner", "member")

    client.post(f"/api/books/{sample_book.id}/borrow", headers=make_headers(patron))
    resp = client.post(f"/api/books/{sample_book.id}/return", headers=make_headers(staff))
    assert resp.status_code == 200


def test_issue_fails_for_suspended_member(client, make_headers, librarian, sample_book, db):
    from app.models import Member
    suspended = Member(membership_number="M-SUSP", full_name="Suspended Patron", status="suspended")
    db.session.add(suspended)
    db.session.commit()

    resp = client.post(
        "/api/circulation/issue",
        json={"bookId": sample_book.id, "memberId": suspended.id},
        headers=make_headers(librarian),
    )
    assert resp.status_code == 400


def test_issue_and_staff_return_workflow(client, make_headers, librarian, sample_book, sample_member):
    issue_resp = client.post(
        "/api/circulation/issue",
        json={"bookId": sample_book.id, "memberId": sample_member.id},
        headers=make_headers(librarian),
    )
    assert issue_resp.status_code == 201
    loan_id = issue_resp.get_json()["id"]

    return_resp = client.post(f"/api/circulation/return/{loan_id}", headers=make_headers(librarian))
    assert return_resp.status_code == 200
    assert return_resp.get_json()["returnedAt"] is not None


def test_cannot_return_already_returned_loan(client, make_headers, librarian, sample_book, sample_member):
    issue_resp = client.post(
        "/api/circulation/issue",
        json={"bookId": sample_book.id, "memberId": sample_member.id},
        headers=make_headers(librarian),
    )
    loan_id = issue_resp.get_json()["id"]
    client.post(f"/api/circulation/return/{loan_id}", headers=make_headers(librarian))

    resp = client.post(f"/api/circulation/return/{loan_id}", headers=make_headers(librarian))
    assert resp.status_code == 400


def test_stats_reflect_borrowed_copies(client, make_headers, librarian, sample_book, sample_member):
    client.post(
        "/api/circulation/issue",
        json={"bookId": sample_book.id, "memberId": sample_member.id},
        headers=make_headers(librarian),
    )
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["totalBorrowed"] >= 1
