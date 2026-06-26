from fastapi import HTTPException, status


def unauthorized(message: str = "请先登录") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": message})


def forbidden(message: str = "你没有权限执行此操作") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"message": message})


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": message})


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": message})
