package com.globalinsure.claims.dto;

import jakarta.validation.constraints.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDate;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PolicyRequest {

    @NotNull(message = "customerId is required")
    private Long customerId;

    @NotBlank(message = "policyType is required")
    @Pattern(regexp = "AUTO|HEALTH|HOME|LIFE", message = "policyType must be one of AUTO, HEALTH, HOME, LIFE")
    private String policyType;

    @NotNull
    @DecimalMin(value = "1000.0", message = "coverageAmount must be at least 1000")
    private BigDecimal coverageAmount;

    @NotNull
    @DecimalMin(value = "1.0", message = "premiumAmount must be positive")
    private BigDecimal premiumAmount;

    @NotNull
    @FutureOrPresent(message = "startDate cannot be in the past")
    private LocalDate startDate;

    @NotNull
    private LocalDate endDate;
}
