package com.example.radi_battery.repository;

import com.example.radi_battery.entity.Voucher;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface VoucherRepository extends JpaRepository<Voucher, Long> {

    Optional<Voucher> findByVoucherCode(String voucherCode);

    List<Voucher> findByCustomerId(Long customerId);

    @Query("SELECT v FROM Voucher v WHERE v.customer.id = :customerId AND v.isUsed = false AND v.validTo > :currentTime")
    List<Voucher> findActiveVouchersByCustomerId(@Param("customerId") Long customerId, @Param("currentTime") LocalDateTime currentTime);

    @Query("SELECT v FROM Voucher v WHERE v.isUsed = false AND v.validTo < :currentTime")
    List<Voucher> findExpiredVouchers(@Param("currentTime") LocalDateTime currentTime);

    @Query("SELECT v FROM Voucher v WHERE v.notificationSent = false")
    List<Voucher> findVouchersToNotify();
}