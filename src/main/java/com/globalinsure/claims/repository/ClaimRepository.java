package com.globalinsure.claims.repository;

import com.globalinsure.claims.domain.Claim;
import com.globalinsure.claims.domain.ClaimStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ClaimRepository extends JpaRepository<Claim, Long> {
    Optional<Claim> findByClaimReference(String claimReference);
    List<Claim> findByStatus(ClaimStatus status);
    List<Claim> findByPolicyId(Long policyId);
}
