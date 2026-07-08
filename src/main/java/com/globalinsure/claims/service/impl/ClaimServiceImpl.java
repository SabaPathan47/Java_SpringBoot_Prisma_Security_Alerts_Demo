package com.globalinsure.claims.service.impl;

import com.globalinsure.claims.domain.Claim;
import com.globalinsure.claims.domain.ClaimStatus;
import com.globalinsure.claims.domain.Policy;
import com.globalinsure.claims.dto.ClaimRequest;
import com.globalinsure.claims.dto.ClaimResponse;
import com.globalinsure.claims.exception.BusinessRuleException;
import com.globalinsure.claims.exception.ResourceNotFoundException;
import com.globalinsure.claims.repository.ClaimRepository;
import com.globalinsure.claims.repository.PolicyRepository;
import com.globalinsure.claims.service.ClaimService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ClaimServiceImpl implements ClaimService {

    private final ClaimRepository claimRepository;
    private final PolicyRepository policyRepository;

    @Override
    @Transactional
    public ClaimResponse fileClaim(ClaimRequest request) {
        Policy policy = policyRepository.findByPolicyNumber(request.getPolicyNumber())
                .orElseThrow(() -> new ResourceNotFoundException(
                        "Policy not found: " + request.getPolicyNumber()));

        if (!policy.isActive()) {
            throw new BusinessRuleException("Cannot file a claim against an inactive policy");
        }
        if (LocalDate.now().isAfter(policy.getEndDate())) {
            throw new BusinessRuleException("Policy has expired, claim cannot be filed");
        }
        if (request.getClaimedAmount().compareTo(policy.getCoverageAmount()) > 0) {
            throw new BusinessRuleException("Claimed amount exceeds policy coverage amount");
        }

        Claim claim = Claim.builder()
                .claimReference(generateClaimReference())
                .policy(policy)
                .claimedAmount(request.getClaimedAmount())
                .incidentDescription(request.getIncidentDescription())
                .status(ClaimStatus.SUBMITTED)
                .submittedAt(LocalDateTime.now())
                .build();

        return toResponse(claimRepository.save(claim));
    }

    @Override
    @Transactional
    public ClaimResponse approveClaim(String claimReference, String reviewerNotes) {
        Claim claim = findClaimOrThrow(claimReference);
        assertTransitionAllowed(claim);
        claim.setStatus(ClaimStatus.APPROVED);
        claim.setReviewerNotes(reviewerNotes);
        claim.setResolvedAt(LocalDateTime.now());
        return toResponse(claimRepository.save(claim));
    }

    @Override
    @Transactional
    public ClaimResponse rejectClaim(String claimReference, String reviewerNotes) {
        Claim claim = findClaimOrThrow(claimReference);
        assertTransitionAllowed(claim);
        claim.setStatus(ClaimStatus.REJECTED);
        claim.setReviewerNotes(reviewerNotes);
        claim.setResolvedAt(LocalDateTime.now());
        return toResponse(claimRepository.save(claim));
    }

    @Override
    public ClaimResponse getClaim(String claimReference) {
        return toResponse(findClaimOrThrow(claimReference));
    }

    @Override
    public List<ClaimResponse> getAllClaims() {
        return claimRepository.findAll().stream().map(this::toResponse).collect(Collectors.toList());
    }

    private void assertTransitionAllowed(Claim claim) {
        if (claim.getStatus() != ClaimStatus.SUBMITTED && claim.getStatus() != ClaimStatus.UNDER_REVIEW) {
            throw new BusinessRuleException(
                    "Claim in status " + claim.getStatus() + " cannot be approved/rejected");
        }
    }

    private Claim findClaimOrThrow(String claimReference) {
        return claimRepository.findByClaimReference(claimReference)
                .orElseThrow(() -> new ResourceNotFoundException("Claim not found: " + claimReference));
    }

    private String generateClaimReference() {
        return "CLM-" + LocalDate.now().getYear() + "-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
    }

    private ClaimResponse toResponse(Claim claim) {
        return ClaimResponse.builder()
                .claimReference(claim.getClaimReference())
                .policyNumber(claim.getPolicy().getPolicyNumber())
                .claimedAmount(claim.getClaimedAmount())
                .status(claim.getStatus())
                .submittedAt(claim.getSubmittedAt())
                .resolvedAt(claim.getResolvedAt())
                .reviewerNotes(claim.getReviewerNotes())
                .build();
    }
}
