CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    national_id VARCHAR(64) NOT NULL UNIQUE,
    date_of_birth DATE
);

CREATE TABLE policies (
    id BIGSERIAL PRIMARY KEY,
    policy_number VARCHAR(64) NOT NULL UNIQUE,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    policy_type VARCHAR(32) NOT NULL,
    coverage_amount NUMERIC(15,2) NOT NULL,
    premium_amount NUMERIC(15,2) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE claims (
    id BIGSERIAL PRIMARY KEY,
    claim_reference VARCHAR(64) NOT NULL UNIQUE,
    policy_id BIGINT NOT NULL REFERENCES policies(id),
    claimed_amount NUMERIC(15,2) NOT NULL,
    incident_description VARCHAR(2000),
    status VARCHAR(32) NOT NULL,
    submitted_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    reviewer_notes VARCHAR(1000)
);

CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    claim_id BIGINT NOT NULL UNIQUE REFERENCES claims(id),
    amount NUMERIC(15,2) NOT NULL,
    status VARCHAR(32) NOT NULL,
    processed_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_policies_customer ON policies(customer_id);
CREATE INDEX idx_claims_policy ON claims(policy_id);
CREATE INDEX idx_claims_status ON claims(status);
