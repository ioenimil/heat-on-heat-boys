package com.servicehub.controller.view;

import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class HomeController {

    @GetMapping("/")
    public String index(Authentication authentication) {
        if (authentication != null
                && authentication.getAuthorities().stream()
                .noneMatch(a -> "ROLE_ANONYMOUS".equals(a.getAuthority()))) {
            return "redirect:/dashboard";
        }
        return "redirect:/login";
    }
}
