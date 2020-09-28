from app.kubeseal import run_kubeseal
from os import environ
import json
import pytest
import logging

LOGGER = logging.getLogger(__name__)
environ["ORIGIN_URL"] = "http://no-server-here"

@pytest.mark.container
@pytest.mark.cluster
def test_post_secrets_object(app, client):
    sealing_request_data = {'namespace': 'foo', 'secret': 'bar', 'secrets': ['my', 'precious']}
    expected_sealing_response_data = {'namespace': 'foo', 'secret': 'bar', 'sealedSecrets': ['kauder', 'welsch']}
    res = client.post('/secrets', data=sealing_request_data)
    assert res.status_code == 200
    assert expected_sealing_response_data == json.loads(res.get_data(as_text=True))

def test_get_api(client):
    # given running http server
    # when GET /secrets
    res = client.get('/secrets')
    # then return non empty result
    assert res.status_code == 200
    assert res.get_data(as_text=True) != ""

@pytest.mark.container
@pytest.mark.cluster
def test_post_api(client):
    # given running http server
    # when POST /secrets
    data = {
        "secret": "test-secret",
        "namespace": "test-namespace",
        "secrets": [{"key": "foo", "value": "bar"}, {"key": "bar", "value": "foo"}]
    }
    res = client.post('/secrets', data=json.dumps(data), headers={"Content-Type": "application/json"})
    # then return non empty result
    assert res.status_code == 200
    assert res.get_data(as_text=True) != ""
