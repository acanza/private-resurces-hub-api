# private-resources-hub-api

A personal project designed to validate the correct functioning of a private resources distribution infrastructure deployed on AWS.

## Project Overview

This is a FastAPI-based REST API that provides secure access to private resources stored in AWS S3. The system integrates with Amazon Cognito for authentication and uses CloudFront for content delivery with signed URLs and cookies for secure access control.

### Key Features

- **Secure Authentication**: Integration with AWS Cognito for bearer token validation
- **Access Control**: Role-based access to different resource categories
- **Signed URLs & Cookies**: CloudFront signed URLs and cookies for secure, time-limited access to resources
- **S3 Integration**: Direct integration with AWS S3 for resource storage and retrieval
- **RESTful API**: Well-documented endpoints using FastAPI's automatic OpenAPI/Swagger documentation

## API Endpoints

### 1. List All Resources with Access Information
- **Method**: `POST`
- **Endpoint**: `/resources/`
- **Authentication**: Bearer token (Cognito)
- **Request Body**: 
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Description**: Lists all directories (categories) in the S3 bucket along with the user's access permissions for each category. Returns a list of resources with access status and corresponding signed URLs.
- **Response**: Array of resources with `name`, `has_access`, and optional `access_url`

### 2. List Items in a Category with Signed URLs
- **Method**: `GET`
- **Endpoint**: `/resources/{category_id}`
- **Authentication**: Bearer token (Cognito)
- **Query Parameters**: 
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Description**: Retrieves all items within a specific category directory from S3, generating CloudFront signed URLs for each item. The user must have access permissions to the requested category.
- **Response**: Array of items with `name` and `signed_url`

### 3. Request Access to a Category
- **Method**: `POST`
- **Endpoint**: `/resources/{category_id}/access`
- **Authentication**: Bearer token (Cognito)
- **Request Body**: 
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Description**: Validates user permissions for the requested category and issues CloudFront signed cookies. These cookies are set in the response headers and can be used by the browser to stream objects directly from CloudFront without requiring individual signed URLs for each request.
- **Response**: 
  ```json
  {
    "cloudfront_url": "https://distribution.cloudfront.net/category_id/",
    "expires_at": 1234567890
  }
  ```

## Project Purpose

This API serves as a validation tool to ensure the following AWS infrastructure components work correctly:
- AWS S3 for resource storage
- AWS Cognito for authentication and authorization
- AWS CloudFront for secure content delivery
- Proper integration and communication between all services
- Secure token handling and signed URL/cookie generation