from src.exceptions import AppError
from src.resources.constants import ErrorCode


class ResourceNotFound(AppError):
    status_code = 404
    detail = ErrorCode.RESOURCE_NOT_FOUND


class ResourceAlreadyExists(AppError):
    status_code = 409
    detail = ErrorCode.RESOURCE_ALREADY_EXISTS


class S3AccessError(AppError):
    status_code = 502
    detail = ErrorCode.S3_ACCESS_ERROR


class DynamoDBAccessError(AppError):
    status_code = 502
    detail = ErrorCode.DYNAMODB_ACCESS_ERROR


class AccessDenied(AppError):
    status_code = 403
    detail = ErrorCode.ACCESS_DENIED


class CloudFrontSigningError(AppError):
    status_code = 502
    detail = ErrorCode.CLOUDFRONT_SIGNING_ERROR
