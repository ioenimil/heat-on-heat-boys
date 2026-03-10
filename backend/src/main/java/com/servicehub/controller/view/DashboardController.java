package com.servicehub.controller.view;

import java.util.Collections;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/dashboard")
public class DashboardController {

    @GetMapping
    public String dashboard(Authentication authentication) {
        if (authentication != null) {
            boolean isAdmin = authentication.getAuthorities().stream()
                    .anyMatch(a -> "ROLE_ADMIN".equals(a.getAuthority()));
            if (isAdmin) {
                return "redirect:/dashboard/admin";
            }

            boolean isAgent = authentication.getAuthorities().stream()
                    .anyMatch(a -> "ROLE_AGENT".equals(a.getAuthority()));
            if (isAgent) {
                return "redirect:/dashboard/agent";
            }
        }
        return "redirect:/dashboard/user";
    }

    @GetMapping("/user")
    public String userDashboard(Model model) {
        model.addAttribute("userRole", "USER");
        model.addAttribute("myOpenCount", 0);
        model.addAttribute("myResolvedCount", 0);
        model.addAttribute("myTickets", Collections.emptyList());
        return "dashboard/user";
    }

    @GetMapping("/agent")
    public String agentDashboard(Model model) {
        model.addAttribute("userRole", "AGENT");
        model.addAttribute("currentWeek", Collections.emptyList());
        return "dashboard/agent";
    }

    @GetMapping("/admin")
    public String adminDashboard(Model model) {
        model.addAttribute("userRole", "ADMIN");

        // KPI headline numbers
        model.addAttribute("totalTickets", 0);
        model.addAttribute("overallCompliance", 0);
        model.addAttribute("totalBreached", 0);
        model.addAttribute("activeBreaches", 0);

        // List data — always empty lists so JS never receives null
        model.addAttribute("atRiskTickets",  Collections.emptyList());
        model.addAttribute("slaMetrics",     Collections.emptyList());
        model.addAttribute("leaderboard",    Collections.emptyList());
        model.addAttribute("deptWorkload",   Collections.emptyList());
        model.addAttribute("dailyVolume",    Collections.emptyList());

        // ETL timestamp — null means "not run yet" (handled in template)
        model.addAttribute("lastEtlRun", null);

        return "dashboard/admin";
    }
}
