package com.globalinsure.claims.service;

import com.globalinsure.claims.domain.Policy;
import com.globalinsure.claims.dto.PolicyRequest;

public interface PolicyService {
    Policy createPolicy(PolicyRequest request);
    Policy getPolicyByNumber(String policyNumber);
}
