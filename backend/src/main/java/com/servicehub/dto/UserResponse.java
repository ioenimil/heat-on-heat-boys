package com.servicehub.dto;

import com.servicehub.model.enums.UserRole;
import java.util.UUID;
import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class UserResponse {
    private UUID id;
    private String email;
    private String name;
    private UserRole role;
    private UUID departmentId;
    private Boolean isActive;
}
