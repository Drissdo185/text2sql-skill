package com.example.radi_battery.dto;

import lombok.Data;

@Data
public class VoucherCreateRequest {
    private Long customerId;
    private Double discountAmount;
    private Double discountPercentage;
    private Double minimumPurchaseAmount;
    private String createdBy;
}