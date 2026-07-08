package com.globalinsure.claims.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI claimsServiceOpenApi() {
        return new OpenAPI().info(new Info()
                .title("GlobalInsure Claims Processing API")
                .version("1.0.0")
                .description("Core microservice for policy and insurance claims lifecycle management"));
    }
}
