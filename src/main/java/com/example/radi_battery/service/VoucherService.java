package com.example.radi_battery.service;

import com.example.radi_battery.entity.Customer;
import com.example.radi_battery.entity.Voucher;
import com.example.radi_battery.repository.VoucherRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Transactional
public class VoucherService {

    private final VoucherRepository voucherRepository;
    private final ZaloNotificationService zaloNotificationService;

    public Voucher createNextPurchaseVoucher(Customer customer, Double discountAmount,
                                           Double discountPercentage, Double minimumPurchaseAmount,
                                           String createdBy) {
        Voucher voucher = new Voucher();
        voucher.setVoucherCode(generateVoucherCode());
        voucher.setCustomer(customer);
        voucher.setDiscountAmount(discountAmount);
        voucher.setDiscountPercentage(discountPercentage);
        voucher.setMinimumPurchaseAmount(minimumPurchaseAmount);
        voucher.setValidFrom(LocalDateTime.now());
        voucher.setValidTo(LocalDateTime.now().plusDays(30)); // Valid for 30 days
        voucher.setCreatedBy(createdBy);

        Voucher savedVoucher = voucherRepository.save(voucher);

        // Send notification via Zalo OA/ZNS
        try {
            zaloNotificationService.sendVoucherNotification(savedVoucher);
            savedVoucher.setNotificationSent(true);
            voucherRepository.save(savedVoucher);
        } catch (Exception e) {
            // Log error but don't fail the voucher creation
            System.err.println("Failed to send voucher notification: " + e.getMessage());
        }

        return savedVoucher;
    }

    public Optional<Voucher> findByVoucherCode(String voucherCode) {
        return voucherRepository.findByVoucherCode(voucherCode);
    }

    public List<Voucher> findVouchersByCustomer(Long customerId) {
        return voucherRepository.findByCustomerId(customerId);
    }

    public List<Voucher> findActiveVouchersByCustomer(Long customerId) {
        return voucherRepository.findActiveVouchersByCustomerId(customerId, LocalDateTime.now());
    }

    public boolean useVoucher(String voucherCode) {
        Optional<Voucher> voucherOpt = voucherRepository.findByVoucherCode(voucherCode);
        if (voucherOpt.isPresent()) {
            Voucher voucher = voucherOpt.get();
            if (!voucher.getIsUsed() && voucher.getValidTo().isAfter(LocalDateTime.now())) {
                voucher.setIsUsed(true);
                voucher.setUsedAt(LocalDateTime.now());
                voucherRepository.save(voucher);
                return true;
            }
        }
        return false;
    }

    public boolean isVoucherValid(String voucherCode, Double purchaseAmount) {
        Optional<Voucher> voucherOpt = voucherRepository.findByVoucherCode(voucherCode);
        if (voucherOpt.isPresent()) {
            Voucher voucher = voucherOpt.get();
            return !voucher.getIsUsed() &&
                   voucher.getValidTo().isAfter(LocalDateTime.now()) &&
                   (voucher.getMinimumPurchaseAmount() == null ||
                    purchaseAmount >= voucher.getMinimumPurchaseAmount());
        }
        return false;
    }

    public Double calculateDiscount(String voucherCode, Double purchaseAmount) {
        Optional<Voucher> voucherOpt = voucherRepository.findByVoucherCode(voucherCode);
        if (voucherOpt.isPresent() && isVoucherValid(voucherCode, purchaseAmount)) {
            Voucher voucher = voucherOpt.get();
            if (voucher.getDiscountAmount() != null) {
                return voucher.getDiscountAmount();
            } else if (voucher.getDiscountPercentage() != null) {
                return purchaseAmount * (voucher.getDiscountPercentage() / 100);
            }
        }
        return 0.0;
    }

    public List<Voucher> findVouchersToNotify() {
        return voucherRepository.findVouchersToNotify();
    }

    public void retryFailedNotifications() {
        List<Voucher> vouchersToNotify = findVouchersToNotify();
        for (Voucher voucher : vouchersToNotify) {
            try {
                zaloNotificationService.sendVoucherNotification(voucher);
                voucher.setNotificationSent(true);
                voucherRepository.save(voucher);
            } catch (Exception e) {
                System.err.println("Failed to send voucher notification for voucher " +
                                 voucher.getVoucherCode() + ": " + e.getMessage());
            }
        }
    }

    private String generateVoucherCode() {
        return "VOUCHER_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
    }
}