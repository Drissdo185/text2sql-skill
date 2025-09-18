package com.example.radi_battery.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ZaloNotificationRequest {

    @JsonProperty("phone")
    private String phone;

    @JsonProperty("template_id")
    private String templateId;

    @JsonProperty("template_data")
    private Map<String, String> templateData;

    @JsonProperty("tracking_id")
    private String trackingId;
}