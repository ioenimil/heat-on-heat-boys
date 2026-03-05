package com.servicehub.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .authorizeHttpRequests(auth -> auth
                        // Public API endpoints
                        .requestMatchers("/api/health/**").permitAll()
                        // Public pages
                        .requestMatchers("/").permitAll()
                        // Vite-built assets (JS, CSS, source maps)
                        .requestMatchers("/assets/**").permitAll()
                        // Loose static files at the root (fallback for any directly referenced files)
                        .requestMatchers("/*.js", "/*.css", "/*.map").permitAll()
                        // Icons and images
                        .requestMatchers("/favicon.ico", "/*.png", "/*.jpg", "/*.jpeg", "/*.gif", "/*.svg", "/*.webp").permitAll()
                        // Fonts
                        .requestMatchers("/*.woff", "/*.woff2", "/*.ttf", "/*.eot").permitAll()
                        .anyRequest().authenticated()
                );

        return http.build();
    }
}

