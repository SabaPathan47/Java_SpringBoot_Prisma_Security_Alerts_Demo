package com.globalinsure.claims.controller;

import com.globalinsure.claims.domain.Policy;
import com.globalinsure.claims.dto.PolicyRequest;
import com.globalinsure.claims.service.PolicyService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/policies")
@RequiredArgsConstructor
public class PolicyController {

    private final PolicyService policyService;

    @PostMapping
    public ResponseEntity<Policy> createPolicy(@Valid @RequestBody PolicyRequest request) {
        Policy created = policyService.createPolicy(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping("/{policyNumber}")
    public ResponseEntity<Policy> getPolicy(@PathVariable String policyNumber) {
        return ResponseEntity.ok(policyService.getPolicyByNumber(policyNumber));
    }
}
