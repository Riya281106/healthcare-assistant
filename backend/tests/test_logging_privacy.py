import logging


def test_response_has_request_id_header(client):
    r = client.get("/")
    assert len(r.headers["X-Request-ID"]) == 12


def test_each_request_gets_a_different_id(client):
    assert client.get("/").headers["X-Request-ID"] != client.get("/").headers["X-Request-ID"]


def test_message_text_is_never_logged(client, alice, caplog):
    secret = "my-very-private-diagnosis-zebra-4471"
    logging.getLogger("healthcare").propagate = True   # let caplog see our logger
    with caplog.at_level(logging.DEBUG, logger="healthcare"):
        client.post("/api/chat", json={"message": secret}, headers=alice["headers"])
    logging.getLogger("healthcare").propagate = False

    assert secret not in caplog.text
    assert "chat request received" in caplog.text      # but the event IS logged


def test_log_lines_carry_request_and_user_ids(client, alice, caplog):
    logging.getLogger("healthcare").propagate = True
    with caplog.at_level(logging.INFO, logger="healthcare"):
        r = client.post("/api/chat", json={"message": "hello"}, headers=alice["headers"])
    logging.getLogger("healthcare").propagate = False

    records = [rec for rec in caplog.records if rec.name == "healthcare.api"]
    assert records
    # the access-log line includes the user id set by the auth dependency
    assert any(f"user={alice['id']}" in rec.getMessage() for rec in records)
