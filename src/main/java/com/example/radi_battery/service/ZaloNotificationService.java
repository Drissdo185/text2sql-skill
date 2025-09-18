package com.example.radi_battery.service;

import com.example.radi_battery.dto.ZaloNotificationRequest;
import com.example.radi_battery.entity.Voucher;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.text.NumberFormat;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class ZaloNotificationService {

    @Value("${zalo.oa.access_token}")
    private String oaAccessToken;

    @Value("${zalo.zns.app_id}")
    private String znsAppId;

    @Value("${zalo.zns.template_id}")
    private String templateId;

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final String ZNS_API_URL = "https://business.openapi.zalo.me/message/template";
    private static final String OA_API_URL = "https://openapi.zalo.me/v2.0/oa/message";

    public void sendVoucherNotification(Voucher voucher) throws Exception {
        if (voucher.getCustomer().getPhoneNumber() != null) {
            sendZNSNotification(voucher);
        } else if (voucher.getCustomer().getZaloUserId() != null) {
            sendOANotification(voucher);
        } else {
            throw new Exception("Customer has no phone number or Zalo User ID for notification");
        }
    }

    private void sendZNSNotification(Voucher voucher) throws Exception {
        HttpHeaders headers = new HttpHeaders();
        headers.set("access_token", oaAccessToken);
        headers.set("Content-Type", "application/json");

        Map<String, String> templateData = new HashMap<>();
        templateData.put("customer_name", voucher.getCustomer().getFullName() != null ?
                        voucher.getCustomer().getFullName() : "Khách hàng");
        templateData.put("voucher_code", voucher.getVoucherCode());
        templateData.put("discount_amount", formatCurrency(voucher.getDiscountAmount()));
        templateData.put("valid_to", voucher.getValidTo().format(DateTimeFormatter.ofPattern("dd/MM/yyyy")));

        if (voucher.getMinimumPurchaseAmount() != null && voucher.getMinimumPurchaseAmount() > 0) {
            templateData.put("minimum_amount", formatCurrency(voucher.getMinimumPurchaseAmount()));
        } else {
            templateData.put("minimum_amount", "Không có");
        }

        ZaloNotificationRequest request = new ZaloNotificationRequest();
        request.setPhone(voucher.getCustomer().getPhoneNumber());
        request.setTemplateId(templateId);
        request.setTemplateData(templateData);
        request.setTrackingId("voucher_" + voucher.getId());

        HttpEntity<ZaloNotificationRequest> entity = new HttpEntity<>(request, headers);

        ResponseEntity<String> response = restTemplate.exchange(
                ZNS_API_URL, HttpMethod.POST, entity, String.class);

        if (response.getStatusCode().is2xxSuccessful()) {
            System.out.println("ZNS notification sent successfully for voucher: " + voucher.getVoucherCode());
        } else {
            throw new Exception("Failed to send ZNS notification: " + response.getBody());
        }
    }

    private void sendOANotification(Voucher voucher) throws Exception {
        HttpHeaders headers = new HttpHeaders();
        headers.set("access_token", oaAccessToken);
        headers.set("Content-Type", "application/json");

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("recipient", Map.of("user_id", voucher.getCustomer().getZaloUserId()));

        String messageText = String.format(
                "🎉 Chúc mừng %s!\n\n" +
                "Bạn đã nhận được voucher giảm giá:\n" +
                "🎫 Mã voucher: %s\n" +
                "💰 Giảm giá: %s\n" +
                "📅 Có hiệu lực đến: %s\n" +
                "%s\n\n" +
                "Sử dụng ngay để nhận ưu đãi tuyệt vời! 🛒",
                voucher.getCustomer().getFullName() != null ? voucher.getCustomer().getFullName() : "Khách hàng",
                voucher.getVoucherCode(),
                formatDiscount(voucher),
                voucher.getValidTo().format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm")),
                voucher.getMinimumPurchaseAmount() != null && voucher.getMinimumPurchaseAmount() > 0 ?
                        "🛍️ Đơn hàng tối thiểu: " + formatCurrency(voucher.getMinimumPurchaseAmount()) :
                        "🆓 Không có điều kiện tối thiểu"
        );

        requestBody.put("message", Map.of("text", messageText));

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        ResponseEntity<String> response = restTemplate.exchange(
                OA_API_URL, HttpMethod.POST, entity, String.class);

        if (response.getStatusCode().is2xxSuccessful()) {
            System.out.println("OA notification sent successfully for voucher: " + voucher.getVoucherCode());
        } else {
            throw new Exception("Failed to send OA notification: " + response.getBody());
        }
    }

    private String formatCurrency(Double amount) {
        if (amount == null) return "0 VND";
        NumberFormat formatter = NumberFormat.getCurrencyInstance(new Locale("vi", "VN"));
        return formatter.format(amount);
    }

    private String formatDiscount(Voucher voucher) {
        if (voucher.getDiscountAmount() != null) {
            return formatCurrency(voucher.getDiscountAmount());
        } else if (voucher.getDiscountPercentage() != null) {
            return voucher.getDiscountPercentage() + "%";
        }
        return "0";
    }
}