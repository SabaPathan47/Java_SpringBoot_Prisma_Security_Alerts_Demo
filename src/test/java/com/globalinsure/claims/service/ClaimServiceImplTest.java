package com.globalinsure.claims.service;

import com.globalinsure.claims.domain.Policy;
import com.globalinsure.claims.dto.ClaimRequest;
import com.globalinsure.claims.dto.ClaimResponse;
import com.globalinsure.claims.exception.BusinessRuleException;
import com.globalinsure.claims.exception.ResourceNotFoundException;
import com.globalinsure.claims.repository.ClaimRepository;
import com.globalinsure.claims.repository.PolicyRepository;
import com.globalinsure.claims.service.impl.ClaimServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

/**
 * Unit tests for ClaimServiceImpl business rules.
 * Report consumed by the Unit Test Analyzer AI Agent in the CI pipeline.
 */
@ExtendWith(MockitoExtension.class)
class ClaimServiceImplTest {

    @Mock
    private ClaimRepository claimRepository;

    @Mock
    private PolicyRepository policyRepository;

    @InjectMocks
    private ClaimServiceImpl claimService;

    private Policy activePolicy;

    @BeforeEach
    void setUp() {
        activePolicy = Policy.builder()
                .id(1L)
                .policyNumber("POL-2026-ABCD1234")
                .policyType("AUTO")
                .coverageAmount(new BigDecimal("50000"))
                .premiumAmount(new BigDecimal("1200"))
                .startDate(LocalDate.now().minusMonths(1))
                .endDate(LocalDate.now().plusMonths(11))
                .active(true)
                .build();
    }

    @Test
    void fileClaim_shouldSucceed_whenPolicyActiveAndAmountWithinCoverage() {
        when(policyRepository.findByPolicyNumber("POL-2026-ABCD1234")).thenReturn(Optional.of(activePolicy));
        when(claimRepository.save(any())).thenAnswer(inv -> {
            var claim = inv.getArgument(0, com.globalinsure.claims.domain.Claim.class);
            claim.setId(100L);
            return claim;
        });

        ClaimRequest request = ClaimRequest.builder()
                .policyNumber("POL-2026-ABCD1234")
                .claimedAmount(new BigDecimal("10000"))
                .incidentDescription("Rear-end collision on highway")
                .build();

        ClaimResponse response = claimService.fileClaim(request);

        assertThat(response.getStatus().name()).isEqualTo("SUBMITTED");
        assertThat(response.getPolicyNumber()).isEqualTo("POL-2026-ABCD1234");
    }

    @Test
    void fileClaim_shouldThrow_whenPolicyNotFound() {
        when(policyRepository.findByPolicyNumber("UNKNOWN")).thenReturn(Optional.empty());

        ClaimRequest request = ClaimRequest.builder()
                .policyNumber("UNKNOWN")
                .claimedAmount(new BigDecimal("1000"))
                .incidentDescription("test")
                .build();

        assertThatThrownBy(() -> claimService.fileClaim(request))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    void fileClaim_shouldThrow_whenPolicyInactive() {
        activePolicy.setActive(false);
        when(policyRepository.findByPolicyNumber("POL-2026-ABCD1234")).thenReturn(Optional.of(activePolicy));

        ClaimRequest request = ClaimRequest.builder()
                .policyNumber("POL-2026-ABCD1234")
                .claimedAmount(new BigDecimal("1000"))
                .incidentDescription("test")
                .build();

        assertThatThrownBy(() -> claimService.fileClaim(request))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("inactive");
    }

    @Test
    void fileClaim_shouldThrow_whenPolicyExpired() {
        activePolicy.setEndDate(LocalDate.now().minusDays(1));
        when(policyRepository.findByPolicyNumber("POL-2026-ABCD1234")).thenReturn(Optional.of(activePolicy));

        ClaimRequest request = ClaimRequest.builder()
                .policyNumber("POL-2026-ABCD1234")
                .claimedAmount(new BigDecimal("1000"))
                .incidentDescription("test")
                .build();

        assertThatThrownBy(() -> claimService.fileClaim(request))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("expired");
    }

    @Test
    void fileClaim_shouldThrow_whenClaimedAmountExceedsCoverage() {
        when(policyRepository.findByPolicyNumber("POL-2026-ABCD1234")).thenReturn(Optional.of(activePolicy));

        ClaimRequest request = ClaimRequest.builder()
                .policyNumber("POL-2026-ABCD1234")
                .claimedAmount(new BigDecimal("999999"))
                .incidentDescription("test")
                .build();

        assertThatThrownBy(() -> claimService.fileClaim(request))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("exceeds");
    }
}
