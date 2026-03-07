package com.servicehub.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.servicehub.dto.UserResponse;
import com.servicehub.dto.UserUpsertRequest;
import com.servicehub.model.Department;
import com.servicehub.model.User;
import com.servicehub.model.enums.RequestCategory;
import com.servicehub.model.enums.UserRole;
import com.servicehub.repository.DepartmentRepository;
import com.servicehub.repository.UserRepository;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
@DisplayName("UserService")
class UserServiceImplTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private DepartmentRepository departmentRepository;

    private UserServiceImpl userService;

    @BeforeEach
    void setUp() {
        userService = new UserServiceImpl(userRepository, departmentRepository);
    }

    @Test
    @DisplayName("create: persists normalized user and defaults isActive to true")
    void createShouldPersistNormalizedUserWithDefaultActive() {
        UUID departmentId = UUID.randomUUID();
        Department department = department(departmentId);
        UserUpsertRequest request = upsertRequest("  USER@Example.com  ", "  Jane Doe  ", UserRole.AGENT);
        request.setDepartmentId(departmentId);
        request.setIsActive(null);

        when(userRepository.existsByEmail("user@example.com")).thenReturn(false);
        when(departmentRepository.findById(departmentId)).thenReturn(Optional.of(department));
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> {
            User saved = invocation.getArgument(0);
            saved.setId(UUID.randomUUID());
            return saved;
        });

        UserResponse response = userService.create(request);

        assertEquals("user@example.com", response.getEmail());
        assertEquals("Jane Doe", response.getName());
        assertEquals(UserRole.AGENT, response.getRole());
        assertEquals(departmentId, response.getDepartmentId());
        assertEquals(Boolean.TRUE, response.getIsActive());
    }

    @Test
    @DisplayName("create: throws CONFLICT when email already exists")
    void createShouldThrowWhenEmailAlreadyExists() {
        UserUpsertRequest request = upsertRequest("existing@amalitech.com", "Existing", UserRole.USER);
        when(userRepository.existsByEmail("existing@amalitech.com")).thenReturn(true);

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> userService.create(request));

        assertEquals(HttpStatus.CONFLICT, exception.getStatusCode());
        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    @DisplayName("create: throws BAD_REQUEST when department does not exist")
    void createShouldThrowWhenDepartmentMissing() {
        UUID missingDepartmentId = UUID.randomUUID();
        UserUpsertRequest request = upsertRequest("new@amalitech.com", "New User", UserRole.ADMIN);
        request.setDepartmentId(missingDepartmentId);

        when(userRepository.existsByEmail("new@amalitech.com")).thenReturn(false);
        when(departmentRepository.findById(missingDepartmentId)).thenReturn(Optional.empty());

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> userService.create(request));

        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    @DisplayName("update: updates all user fields and saves")
    void updateShouldApplyChangesAndSave() {
        UUID userId = UUID.randomUUID();
        UUID departmentId = UUID.randomUUID();
        User existing = existingUser(userId);
        Department department = department(departmentId);
        UserUpsertRequest request = upsertRequest("updated@amalitech.com", "Updated User", UserRole.ADMIN);
        request.setDepartmentId(departmentId);
        request.setIsActive(Boolean.FALSE);

        when(userRepository.findById(userId)).thenReturn(Optional.of(existing));
        when(userRepository.existsByEmailAndIdNot("updated@amalitech.com", userId)).thenReturn(false);
        when(departmentRepository.findById(departmentId)).thenReturn(Optional.of(department));
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> invocation.getArgument(0));

        UserResponse response = userService.update(userId, request);

        assertEquals(userId, response.getId());
        assertEquals("updated@amalitech.com", response.getEmail());
        assertEquals("Updated User", response.getName());
        assertEquals(UserRole.ADMIN, response.getRole());
        assertEquals(departmentId, response.getDepartmentId());
        assertEquals(Boolean.FALSE, response.getIsActive());
    }

    @Test
    @DisplayName("update: throws NOT_FOUND when user does not exist")
    void updateShouldThrowWhenUserMissing() {
        UUID userId = UUID.randomUUID();
        UserUpsertRequest request = upsertRequest("u@amalitech.com", "User", UserRole.USER);
        when(userRepository.findById(userId)).thenReturn(Optional.empty());

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> userService.update(userId, request));

        assertEquals(HttpStatus.NOT_FOUND, exception.getStatusCode());
    }

    @Test
    @DisplayName("update: throws CONFLICT when another user already has email")
    void updateShouldThrowWhenEmailConflicts() {
        UUID userId = UUID.randomUUID();
        User existing = existingUser(userId);
        UserUpsertRequest request = upsertRequest("duplicate@amalitech.com", "Dup", UserRole.USER);

        when(userRepository.findById(userId)).thenReturn(Optional.of(existing));
        when(userRepository.existsByEmailAndIdNot("duplicate@amalitech.com", userId)).thenReturn(true);

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> userService.update(userId, request));

        assertEquals(HttpStatus.CONFLICT, exception.getStatusCode());
        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    @DisplayName("delete: removes user when id exists")
    void deleteShouldRemoveUser() {
        UUID userId = UUID.randomUUID();
        User existing = existingUser(userId);
        when(userRepository.findById(userId)).thenReturn(Optional.of(existing));

        userService.delete(userId);

        verify(userRepository).delete(existing);
    }

    @Test
    @DisplayName("delete: throws NOT_FOUND when id is missing")
    void deleteShouldThrowWhenUserMissing() {
        UUID userId = UUID.randomUUID();
        when(userRepository.findById(userId)).thenReturn(Optional.empty());

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> userService.delete(userId));

        assertEquals(HttpStatus.NOT_FOUND, exception.getStatusCode());
    }

    @Test
    @DisplayName("update: sets default isActive true when request value is null")
    void updateShouldDefaultActiveWhenNull() {
        UUID userId = UUID.randomUUID();
        User existing = existingUser(userId);
        UserUpsertRequest request = upsertRequest("fresh@amalitech.com", "Fresh", UserRole.AGENT);
        request.setDepartmentId(null);
        request.setIsActive(null);

        when(userRepository.findById(userId)).thenReturn(Optional.of(existing));
        when(userRepository.existsByEmailAndIdNot("fresh@amalitech.com", userId)).thenReturn(false);
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> invocation.getArgument(0));

        UserResponse response = userService.update(userId, request);

        assertEquals(Boolean.TRUE, response.getIsActive());
        assertNull(response.getDepartmentId());
    }

    private UserUpsertRequest upsertRequest(String email, String name, UserRole role) {
        UserUpsertRequest request = new UserUpsertRequest();
        request.setEmail(email);
        request.setName(name);
        request.setRole(role);
        return request;
    }

    private User existingUser(UUID id) {
        User user = new User();
        user.setId(id);
        user.setEmail("current@amalitech.com");
        user.setName("Current User");
        user.setRole(UserRole.USER);
        user.setIsActive(Boolean.TRUE);
        return user;
    }

    private Department department(UUID id) {
        Department department = new Department();
        department.setId(id);
        department.setName("IT");
        department.setCategory(RequestCategory.IT_SUPPORT);
        return department;
    }
}
