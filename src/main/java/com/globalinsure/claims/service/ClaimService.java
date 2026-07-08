package com.globalinsure.claims.service;

import com.globalinsure.claims.dto.ClaimRequest;
import com.globalinsure.claims.dto.ClaimResponse;

import java.util.List;

public interface ClaimService {
    ClaimResponse fileClaim(ClaimRequest request);
    ClaimResponse approveClaim(String claimReference, String reviewerNotes);
    ClaimResponse rejectClaim(String claimReference, String reviewerNotes);
    ClaimResponse getClaim(String claimReference);
    List<ClaimResponse> getAllClaims();
}
