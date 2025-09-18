package com.example.radi_battery.service;

import com.example.radi_battery.entity.Customer;
import com.example.radi_battery.repository.CustomerRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Transactional
public class CustomerService {

    private final CustomerRepository customerRepository;

    public Optional<Customer> findById(Long id) {
        return customerRepository.findById(id);
    }

    public Optional<Customer> findByZaloUserId(String zaloUserId) {
        return customerRepository.findByZaloUserId(zaloUserId);
    }

    public Optional<Customer> findByPhoneNumber(String phoneNumber) {
        return customerRepository.findByPhoneNumber(phoneNumber);
    }

    public List<Customer> searchCustomers(String keyword) {
        if (keyword == null || keyword.trim().isEmpty()) {
            return customerRepository.findAll();
        }
        return customerRepository.searchCustomers(keyword.trim());
    }

    public List<Customer> findActiveCustomers() {
        return customerRepository.findByIsActiveTrue();
    }

    public Customer createCustomer(Customer customer) {
        return customerRepository.save(customer);
    }

    public Customer updateCustomer(Customer customer) {
        return customerRepository.save(customer);
    }

    public void updatePurchaseStats(Long customerId, Double purchaseAmount) {
        Optional<Customer> customerOpt = customerRepository.findById(customerId);
        if (customerOpt.isPresent()) {
            Customer customer = customerOpt.get();
            customer.setTotalPurchases(customer.getTotalPurchases() + purchaseAmount);
            customer.setPurchaseCount(customer.getPurchaseCount() + 1);
            customerRepository.save(customer);
        }
    }

    public void deactivateCustomer(Long customerId) {
        Optional<Customer> customerOpt = customerRepository.findById(customerId);
        if (customerOpt.isPresent()) {
            Customer customer = customerOpt.get();
            customer.setIsActive(false);
            customerRepository.save(customer);
        }
    }

    public List<Customer> findCustomersByMinimumPurchase(Double minAmount) {
        return customerRepository.findByMinimumPurchaseAmount(minAmount);
    }
}