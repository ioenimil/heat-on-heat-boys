package com.servicehub.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.CsrfConfigurer;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;


@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(
            HttpSecurity http,
            RoleBasedAuthenticationSuccessHandler successHandler) throws Exception {
        http
                .csrf(this::configureCsrf)
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/", "/login", "/register", "/error").permitAll()
                        .requestMatchers("/assets/**", "/favicon.ico").permitAll()
                        .requestMatchers("/api/**").permitAll()
                        .requestMatchers("/admin/**", "/dashboard/admin").hasRole("ADMIN")
                        .requestMatchers("/agent/**", "/dashboard/agent").hasRole("AGENT")
                        .requestMatchers("/requests/assigned", "/requests/open", "/requests/*/assign")
                            .hasRole("AGENT")
                        .requestMatchers(
                                "/dashboard/user",
                                "/profile/**",
                                "/requests",
                                "/requests/new",
                                "/requests/history")
                            .hasRole("USER")
                        .anyRequest().authenticated()
                )
                .formLogin(form -> form
                        .loginPage("/login")
                        .successHandler(successHandler)
                        .failureUrl("/login?error")
                        .permitAll()
                )
                .logout(logout -> logout
                        .logoutUrl("/logout")
                        .logoutSuccessUrl("/login?logout")
                        .permitAll()
                )
                .exceptionHandling(ex -> ex
                        .accessDeniedPage("/login?denied")
                );

        return http.build();
    }

    private void configureCsrf(CsrfConfigurer<HttpSecurity> csrf) {
        csrf.ignoringRequestMatchers("/api/**");
    }
}
