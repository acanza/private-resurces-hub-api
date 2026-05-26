from src.exceptions import AppException
from src.resources.constants import ErrorCode


class ResourceNotFound(AppException):
    status_code = 404
    detail = ErrorCode.RESOURCE_NOT_FOUND


class ResourceAlreadyExists(AppException):
    status_code = 409
    detail = ErrorCode.RESOURCE_ALREADY_EXISTS


class S3AccessError(AppException):
    status_code = 502
    detail = ErrorCode.S3_ACCESS_ERROR


class DynamoDBAccessError(AppException):
    status_code = 502
    detail = ErrorCode.DYNAMODB_ACCESS_ERROR
