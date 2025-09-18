package com.example.radi_battery.controller;

import com.example.radi_battery.dto.ApiResponse;
import com.example.radi_battery.dto.VoucherCreateRequest;
import com.example.radi_battery.entity.Customer;
import com.example.radi_battery.entity.Voucher;
import com.example.radi_battery.service.CustomerService;
import com.example.radi_battery.service.VoucherService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/vouchers")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class VoucherController {

    private final VoucherService voucherService;
    private final CustomerService customerService;

    @PostMapping("/create")
    public ResponseEntity<ApiResponse<Voucher>> createVoucher(@RequestBody VoucherCreateRequest request) {
        try {
            Optional<Customer> customer = customerService.findById(request.getCustomerId());
            if (customer.isEmpty()) {
                return ResponseEntity.badRequest().body(ApiResponse.error("Customer not found"));
            }

            if (request.getDiscountAmount() == null && request.getDiscountPercentage() == null) {
                return ResponseEntity.badRequest().body(ApiResponse.error("Either discount amount or percentage is required"));
            }

            Voucher voucher = voucherService.createNextPurchaseVoucher(
                    customer.get(),
                    request.getDiscountAmount(),
                    request.getDiscountPercentage(),
                    request.getMinimumPurchaseAmount(),
                    request.getCreatedBy()
            );

            return ResponseEntity.ok(ApiResponse.success("Voucher created and notification sent", voucher));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ApiResponse.error("Failed to create voucher: " + e.getMessage()));
        }
    }

    @GetMapping("/code/{voucherCode}")
    public ResponseEntity<ApiResponse<Voucher>> getVoucherByCode(@PathVariable String voucherCode) {
        Optional<Voucher> voucher = voucherService.findByVoucherCode(voucherCode);
        if (voucher.isPresent()) {
            return ResponseEntity.ok(ApiResponse.success(voucher.get()));
        }
        return ResponseEntity.notFound().build();
    }

    @GetMapping("/customer/{customerId}")
    public ResponseEntity<ApiResponse<List<Voucher>>> getVouchersByCustomer(@PathVariable Long customerId) {
        List<Voucher> vouchers = voucherService.findVouchersByCustomer(customerId);
        return ResponseEntity.ok(ApiResponse.success("Found " + vouchers.size() + " vouchers", vouchers));
    }

    @GetMapping("/customer/{customerId}/active")
    public ResponseEntity<ApiResponse<List<Voucher>>> getActiveVouchersByCustomer(@PathVariable Long customerId) {
        List<Voucher> vouchers = voucherService.findActiveVouchersByCustomer(customerId);
        return ResponseEntity.ok(ApiResponse.success("Found " + vouchers.size() + " active vouchers", vouchers));
    }

    @PostMapping("/use/{voucherCode}")
    public ResponseEntity<ApiResponse<String>> useVoucher(@PathVariable String voucherCode) {
        boolean success = voucherService.useVoucher(voucherCode);
        if (success) {
            return ResponseEntity.ok(ApiResponse.success("Voucher used successfully"));
        }
        return ResponseEntity.badRequest().body(ApiResponse.error("Voucher is invalid, expired, or already used"));
    }

    @GetMapping("/validate/{voucherCode}")
    public ResponseEntity<ApiResponse<Boolean>> validateVoucher(@PathVariable String voucherCode,
                                                              @RequestParam Double purchaseAmount) {
        boolean isValid = voucherService.isVoucherValid(voucherCode, purchaseAmount);
        return ResponseEntity.ok(ApiResponse.success("Voucher validation result", isValid));
    }

    @GetMapping("/discount/{voucherCode}")
    public ResponseEntity<ApiResponse<Double>> calculateDiscount(@PathVariable String voucherCode,
                                                               @RequestParam Double purchaseAmount) {
        Double discount = voucherService.calculateDiscount(voucherCode, purchaseAmount);
        return ResponseEntity.ok(ApiResponse.success("Calculated discount amount", discount));
    }

    @PostMapping("/retry-notifications")
    public ResponseEntity<ApiResponse<String>> retryFailedNotifications() {
        try {
            voucherService.retryFailedNotifications();
            return ResponseEntity.ok(ApiResponse.success("Failed notifications retry process completed"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ApiResponse.error("Failed to retry notifications: " + e.getMessage()));
        }
    }

    @GetMapping("/pending-notifications")
    public ResponseEntity<ApiResponse<List<Voucher>>> getPendingNotifications() {
        List<Voucher> vouchers = voucherService.findVouchersToNotify();
        return ResponseEntity.ok(ApiResponse.success("Found " + vouchers.size() + " vouchers pending notification", vouchers));
    }
}