package com.servicehub.dto;

import com.servicehub.model.enums.UserRole;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class UserUpsertRequest {

    @NotBlank(message = "email is required")
    @Email(message = "email must be valid")
    private String email;

    @NotBlank(message = "name is required")
    private String name;

    @NotNull(message = "role is required")
    private UserRole role;

    private UUID departmentId;
    private Boolean isActive;
}
