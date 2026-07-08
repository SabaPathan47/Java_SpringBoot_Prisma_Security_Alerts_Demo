package com.globalinsure.claims.service.impl;

import com.globalinsure.claims.domain.Customer;
import com.globalinsure.claims.domain.Policy;
import com.globalinsure.claims.dto.PolicyRequest;
import com.globalinsure.claims.exception.BusinessRuleException;
import com.globalinsure.claims.exception.ResourceNotFoundException;
import com.globalinsure.claims.repository.CustomerRepository;
import com.globalinsure.claims.repository.PolicyRepository;
import com.globalinsure.claims.service.PolicyService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class PolicyServiceImpl implements PolicyService {

    private final PolicyRepository policyRepository;
    private final CustomerRepository customerRepository;

    @Override
    @Transactional
    public Policy createPolicy(PolicyRequest request) {
        if (!request.getEndDate().isAfter(request.getStartDate())) {
            throw new BusinessRuleException("endDate must be after startDate");
        }

        Customer customer = customerRepository.findById(request.getCustomerId())
                .orElseThrow(() -> new ResourceNotFoundException(
                        "Customer not found with id: " + request.getCustomerId()));

        Policy policy = Policy.builder()
                .policyNumber(generatePolicyNumber())
                .customer(customer)
                .policyType(request.getPolicyType())
                .coverageAmount(request.getCoverageAmount())
                .premiumAmount(request.getPremiumAmount())
                .startDate(request.getStartDate())
                .endDate(request.getEndDate())
                .active(true)
                .build();

        return policyRepository.save(policy);
    }

    @Override
    public Policy getPolicyByNumber(String policyNumber) {
        return policyRepository.findByPolicyNumber(policyNumber)
                .orElseThrow(() -> new ResourceNotFoundException("Policy not found: " + policyNumber));
    }

    private String generatePolicyNumber() {
        return "POL-" + LocalDate.now().getYear() + "-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
    }
}
