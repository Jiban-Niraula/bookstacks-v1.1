def test_list_books_is_public(client, sample_book):
    resp = client.get("/api/books")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert sample_book.title in titles


def test_search_books_by_title(client, sample_book):
    resp = client.get("/api/books/search?q=Driven")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_search_books_no_match(client, sample_book):
    resp = client.get("/api/books/search?q=Nonexistent")
    assert resp.get_json() == []


def test_add_book_requires_title_and_author(client, make_headers, librarian):
    resp = client.post("/api/books", json={"title": "Missing Author"}, headers=make_headers(librarian))
    assert resp.status_code == 400


def test_add_book_defaults_copies_to_one(client, make_headers, librarian):
    resp = client.post(
        "/api/books", json={"title": "T", "author": "A"}, headers=make_headers(librarian)
    )
    assert resp.status_code == 201
    assert resp.get_json()["totalCopies"] == 1


def test_delete_nonexistent_book_returns_404(client, make_headers, librarian):
    resp = client.delete("/api/books/99999", headers=make_headers(librarian))
    assert resp.status_code == 404


def test_cannot_delete_book_that_is_currently_borrowed(
    client, make_headers, librarian, sample_book, sample_member
):
    client.post(
        "/api/circulation/issue",
        json={"bookId": sample_book.id, "memberId": sample_member.id},
        headers=make_headers(librarian),
    )
    resp = client.delete(f"/api/books/{sample_book.id}", headers=make_headers(librarian))
    assert resp.status_code == 400
