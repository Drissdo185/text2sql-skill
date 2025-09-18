package com.example.radi_battery.repository;

import com.example.radi_battery.entity.Customer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CustomerRepository extends JpaRepository<Customer, Long> {

    Optional<Customer> findByZaloUserId(String zaloUserId);

    Optional<Customer> findByPhoneNumber(String phoneNumber);

    @Query("SELECT c FROM Customer c WHERE " +
           "LOWER(c.fullName) LIKE LOWER(CONCAT('%', :keyword, '%')) OR " +
           "c.phoneNumber LIKE CONCAT('%', :keyword, '%') OR " +
           "c.email LIKE LOWER(CONCAT('%', :keyword, '%'))")
    List<Customer> searchCustomers(@Param("keyword") String keyword);

    List<Customer> findByIsActiveTrue();

    @Query("SELECT c FROM Customer c WHERE c.totalPurchases >= :minAmount")
    List<Customer> findByMinimumPurchaseAmount(@Param("minAmount") Double minAmount);
}