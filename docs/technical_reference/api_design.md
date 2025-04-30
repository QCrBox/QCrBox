# API Design

This page is a technical reference for the API design of QCrBox.

## API Structure

### Endpoints

This defines the interface for the API and is located in
`pyqcrbox.registry.service.api.api_endpoints`.

### API Helpers

This defines most of the logic of the API and is located in
`pyqcrbox.registry.service.api.api_helpers`.

### QCrBoxResponse

This defines the response class, `QCrBoxResponse` for returning responses from
the APIs. This is a wrapper around `litestar.Response` adding a timestamp to
responses. This is defined in `pyqcrbox.registry.shared.qcrbox_response`.

## Responses

### Successful Responses

```json
{
  "status": "success",
  "message": "Retrieved applications",
  "data": {
    "applications": [
      ...
    ]
  },
  "timestamp": "2025-04-29T15:08:30.188939+00:00Z"
}
```

### Error Responses

```json
{
  "status": "error",
  "error": {
    "code": 400,
    "message": "Bad request",
    "details": null
  },
  "timestamp": "2025-04-29T15:08:30.188939+00:00Z"
}
```
