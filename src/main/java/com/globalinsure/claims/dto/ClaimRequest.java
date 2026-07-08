package com.globalinsure.claims.dto;

import jakarta.validation.constraints.*;
import lombok.*;

import java.math.BigDecimal;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ClaimRequest {

    @NotBlank(message = "policyNumber is required")
    private String policyNumber;

    @NotNull
    @DecimalMin(value = "0.01", message = "claimedAmount must be positive")
    private BigDecimal claimedAmount;

    @NotBlank(message = "incidentDescription is required")
    @Size(max = 2000)
    private String incidentDescription;
}
