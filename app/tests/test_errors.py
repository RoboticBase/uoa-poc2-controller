import importlib

from flask import jsonify, abort

import pytest
import lazy_import


@pytest.fixture
def errors(mocker):
    errors = lazy_import.lazy_module('src.errors')
    errors.logger = mocker.MagicMock()
    yield errors
    importlib.reload(errors)


class DummyException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.description = {'msg': args[0]}


class TestErrorHandler:

    def test_success(self, mocker, app, errors):
        app.register_blueprint(errors.app)

        @app.route('/')
        def test():
            return jsonify({'result': 'success'})

        response = app.test_client().get('/')
        assert response.status_code == 200
        assert response.json == {'result': 'success'}
        assert errors.logger.error.call_count == 0
        assert errors.logger.warning.call_count == 0

    @pytest.mark.parametrize('exception, expected_json, logger_args', [
        (Exception(), {}, ('',)),
        (DummyException('test'), {'msg': 'test'}, ('test',)),
        (NotImplementedError('test'), {}, ('test',)),
    ])
    def test_exception(self, app, errors, exception, expected_json, logger_args):
        app.register_blueprint(errors.app)

        @app.route('/')
        def test():
            raise exception

        response = app.test_client().get('/')
        assert response.status_code == 500
        assert response.json == expected_json
        assert errors.logger.error.call_count == 1
        assert errors.logger.error.call_args[0] == logger_args
        assert errors.logger.warning.call_count == 0

    @pytest.mark.parametrize('status_code, description, expected_json, logger_args', [
        (
            400, {'msg': 'status_code==400'}, {'msg': 'status_code==400'},
            ("400 Bad Request: {'msg': 'status_code==400'}",),
        ),
        (
            401, {'msg': 'status_code==401'}, {'msg': 'status_code==401'},
            ("401 Unauthorized: {'msg': 'status_code==401'}",),
        ),
        (
            403, {'msg': 'status_code==403'}, {'msg': 'status_code==403'},
            ("403 Forbidden: {'msg': 'status_code==403'}",),
        ),
        (
            404, {'msg': 'status_code==404'}, {'msg': 'status_code==404'},
            ("404 Not Found: {'msg': 'status_code==404'}",),
        ),
        (
            405, {'msg': 'status_code==405'}, 'The method is not allowed for the requested URL.',
            ('405 Method Not Allowed: The method is not allowed for the requested URL.',),
        ),
        (
            412, {'msg': 'status_code==412'}, {'msg': 'status_code==412'},
            ("412 Precondition Failed: {'msg': 'status_code==412'}",),
        ),
        (
            422, {'msg': 'status_code==422'}, {'msg': 'status_code==422'},
            ("422 Unprocessable Entity: {'msg': 'status_code==422'}",),
        ),
        (
            423, {'msg': 'status_code==423'}, {'msg': 'status_code==423'},
            ("423 Locked: {'msg': 'status_code==423'}",),
        ),
        (
            408, {'msg': 'status_code==408'}, {'msg': 'status_code==408'},
            ("408 Request Timeout: {'msg': 'status_code==408'}",),
        ),
    ])
    def test_abort_warn(self, app, errors, status_code, description, expected_json, logger_args):
        app.register_blueprint(errors.app)

        @app.route('/')
        def test():
            abort(status_code, description)

        response = app.test_client().get('/')
        assert response.status_code == status_code
        assert response.json == expected_json
        assert errors.logger.error.call_count == 0
        assert errors.logger.warning.call_count == 1
        assert errors.logger.warning.call_args[0] == logger_args

    @pytest.mark.parametrize('status_code, description, expected_json, logger_args', [
        (
            500, {'msg': 'status_code==500'}, {'msg': 'status_code==500'},
            ("500 Internal Server Error: {'msg': 'status_code==500'}",),
        ),
        (
            501, {'msg': 'status_code==501'}, {'msg': 'status_code==501'},
            ("501 Not Implemented: {'msg': 'status_code==501'}",),
        ),
    ])
    def test_abort_error(self, app, errors, status_code, description, expected_json, logger_args):
        app.register_blueprint(errors.app)

        @app.route('/')
        def test():
            abort(status_code, description)

        response = app.test_client().get('/')
        assert response.status_code == status_code
        assert response.json == expected_json
        assert errors.logger.error.call_count == 1
        assert errors.logger.error.call_args[0] == logger_args
        assert errors.logger.warning.call_count == 0
