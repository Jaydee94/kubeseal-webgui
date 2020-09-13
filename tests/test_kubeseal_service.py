import json
from app import run_kubeseal
import pytest
import logging

LOGGER = logging.getLogger(__name__)

#@pytest.mark.container
#@pytest.mark.cluster
def test_get_api(app, client):
    sealing_request_data = {'namespace': 'foo', 'secret': 'bar', 'secrets': ['my', 'precious']}
    expected_sealing_response_data = {'namespace': 'foo', 'secret': 'bar', 'sealedSecrets': ['kauder', 'welsch']}
    res = client.post('/secrets', data=sealing_request_data)
    assert res.status_code == 200
    assert expected_sealing_response_data == json.loads(res.get_data(as_text=True))

#@pytest.mark.container
#@pytest.mark.cluster
def test_run_kubeseal_with_cli():
    # given run test against cli with test cluster
    # when run_kubeseal is called
    # then return valid encrypted secret
    pass

def test_run_kubeseal_without_cli():
    # given no kubeseal cli or kubernetes cluster
    # when run_kubeseal is called
    # then raise RuntimeError
    with pytest.raises(RuntimeError):
        run_kubeseal([""], "", "")

def test_run_kubeseal_without_input():
    # given no secrets to seal
    # when run_kubeseal is called
    sealedSecrets = run_kubeseal([], "", "")
    # then return empty list
    assert sealedSecrets == []
