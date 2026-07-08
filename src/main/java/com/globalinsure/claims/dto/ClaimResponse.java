package com.globalinsure.claims.dto;

import com.globalinsure.claims.domain.ClaimStatus;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ClaimResponse {
    private String claimReference;
    private String policyNumber;
    private BigDecimal claimedAmount;
    private ClaimStatus status;
    private LocalDateTime submittedAt;
    private LocalDateTime resolvedAt;
    private String reviewerNotes;
}
