package com.example.radi_battery.dto;

import lombok.Data;

@Data
public class CustomerSearchRequest {
    private String keyword;
    private String searchType; // "name", "phone", "email", "all"
}