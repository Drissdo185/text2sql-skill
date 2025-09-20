package com.example.radi_battery.service.impl;

import com.example.radi_battery.entity.Customer;
import com.example.radi_battery.repository.CustomerRepository;
import com.example.radi_battery.service.CustomerService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class CustomerServiceImpl implements CustomerService {

    private final CustomerRepository customerRepository;

    @Override
    public Optional<Customer> getCustomerById(Long id) {
        return customerRepository.findById(id);
    }

    @Override
    public Optional<Customer> getCustomerByZaloUserId(String zaloUserId) {
        return customerRepository.findByZaloUserId(zaloUserId);
    }

    @Override
    public Optional<Customer> getCustomerByPhoneNumber(String phoneNumber) {
        return customerRepository.findByPhoneNumber(phoneNumber);
    }

    @Override
    public List<Customer> searchCustomersByKeyword(String keyword) {
        return customerRepository.findByKeyword(keyword);
    }

    @Override
    public List<Customer> getAllCustomers() {
        return customerRepository.findAll();
    }

    @Override
    public Customer createCustomer(Customer customer) {
        customer.setCreatedAt(Instant.now());
        return customerRepository.save(customer);
    }

    @Override
    public Optional<Customer> updateCustomer(Long id, Customer customerDetails) {
        return customerRepository.findById(id)
                .map(customer -> {
                    customer.setName(customerDetails.getName());
                    customer.setPhoneNumber(customerDetails.getPhoneNumber());
                    customer.setBirthdate(customerDetails.getBirthdate());
                    customer.setZaloUserId(customerDetails.getZaloUserId());
                    return customerRepository.save(customer);
                });
    }

    @Override
    public boolean deleteCustomer(Long id) {
        if (customerRepository.existsById(id)) {
            customerRepository.deleteById(id);
            return true;
        }
        return false;
    }
}