package com.servicehub.service.impl;

import com.servicehub.dto.UserResponse;
import com.servicehub.dto.UserUpsertRequest;
import com.servicehub.model.Department;
import com.servicehub.model.User;
import com.servicehub.repository.DepartmentRepository;
import com.servicehub.repository.UserRepository;
import com.servicehub.service.UserService;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {

    private final UserRepository userRepository;
    private final DepartmentRepository departmentRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    @Transactional
    public UserResponse create(UserUpsertRequest request) {
        String normalizedEmail = request.getEmail().trim().toLowerCase();
        if (userRepository.existsByEmail(normalizedEmail)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Email already exists");
        }

        User user = new User();
        user.setEmail(normalizedEmail);
        user.setName(request.getName().trim());
        user.setPasswordHash(resolvePasswordHashOnCreate(request.getPassword()));
        user.setRole(request.getRole());
        user.setDepartment(resolveDepartment(request.getDepartmentId()));
        user.setIsActive(request.getIsActive() == null ? Boolean.TRUE : request.getIsActive());

        return toResponse(userRepository.save(user));
    }

    @Override
    @Transactional
    public UserResponse update(UUID id, UserUpsertRequest request) {
        User user = getUserOrThrow(id);
        String normalizedEmail = request.getEmail().trim().toLowerCase();
        if (userRepository.existsByEmailAndIdNot(normalizedEmail, id)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Email already exists");
        }

        user.setEmail(normalizedEmail);
        user.setName(request.getName().trim());
        if (request.getPassword() != null && !request.getPassword().isBlank()) {
            user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        }
        user.setRole(request.getRole());
        user.setDepartment(resolveDepartment(request.getDepartmentId()));
        user.setIsActive(request.getIsActive() == null ? Boolean.TRUE : request.getIsActive());

        return toResponse(userRepository.save(user));
    }

    @Override
    @Transactional
    public void delete(UUID id) {
        User user = getUserOrThrow(id);
        userRepository.delete(user);
    }

    private User getUserOrThrow(UUID id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
    }

    private Department resolveDepartment(UUID departmentId) {
        if (departmentId == null) {
            return null;
        }
        return departmentRepository.findById(departmentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "Department not found"));
    }

    private String resolvePasswordHashOnCreate(String rawPassword) {
        if (rawPassword == null || rawPassword.isBlank()) {
            return "{noop}password123";
        }
        return passwordEncoder.encode(rawPassword);
    }

    private UserResponse toResponse(User user) {
        return UserResponse.builder()
                .id(user.getId())
                .email(user.getEmail())
                .name(user.getName())
                .role(user.getRole())
                .departmentId(user.getDepartment() == null ? null : user.getDepartment().getId())
                .isActive(user.getIsActive())
                .build();
    }
}
