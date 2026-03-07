package com.servicehub.service;

import com.servicehub.dto.UserResponse;
import com.servicehub.dto.UserUpsertRequest;
import java.util.UUID;

public interface UserService {
    UserResponse create(UserUpsertRequest request);

    UserResponse update(UUID id, UserUpsertRequest request);

    void delete(UUID id);
}
