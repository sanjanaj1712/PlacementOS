def test_cors_allows_configured_origin(client):
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert response.headers["Access-Control-Allow-Origin"] == (
        "http://localhost:3000"
    )
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_cors_blocks_unknown_origin(client):
    response = client.get("/", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in response.headers
