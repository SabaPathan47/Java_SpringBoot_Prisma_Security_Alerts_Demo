package com.globalinsure.claims.controller;

import com.globalinsure.claims.dto.ClaimRequest;
import com.globalinsure.claims.dto.ClaimResponse;
import com.globalinsure.claims.service.ClaimService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/claims")
@RequiredArgsConstructor
public class ClaimController {

    private final ClaimService claimService;

    @PostMapping
    public ResponseEntity<ClaimResponse> fileClaim(@Valid @RequestBody ClaimRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(claimService.fileClaim(request));
    }

    @PutMapping("/{claimReference}/approve")
    public ResponseEntity<ClaimResponse> approveClaim(@PathVariable String claimReference,
                                                        @RequestParam(required = false) String notes) {
        return ResponseEntity.ok(claimService.approveClaim(claimReference, notes));
    }

    @PutMapping("/{claimReference}/reject")
    public ResponseEntity<ClaimResponse> rejectClaim(@PathVariable String claimReference,
                                                       @RequestParam(required = false) String notes) {
        return ResponseEntity.ok(claimService.rejectClaim(claimReference, notes));
    }

    @GetMapping("/{claimReference}")
    public ResponseEntity<ClaimResponse> getClaim(@PathVariable String claimReference) {
        return ResponseEntity.ok(claimService.getClaim(claimReference));
    }

    @GetMapping
    public ResponseEntity<List<ClaimResponse>> getAllClaims() {
        return ResponseEntity.ok(claimService.getAllClaims());
    }
}
