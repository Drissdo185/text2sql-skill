package com.example.radi_battery.controller;

import com.example.radi_battery.dto.ApiResponse;
import com.example.radi_battery.dto.CustomerSearchRequest;
import com.example.radi_battery.entity.Customer;
import com.example.radi_battery.service.CustomerService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/customers")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class CustomerController {

    private final CustomerService customerService;

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<Customer>> getCustomerById(@PathVariable Long id) {
        Optional<Customer> customer = customerService.findById(id);
        if (customer.isPresent()) {
            return ResponseEntity.ok(ApiResponse.success(customer.get()));
        }
        return ResponseEntity.notFound().build();
    }

    @GetMapping("/zalo/{zaloUserId}")
    public ResponseEntity<ApiResponse<Customer>> getCustomerByZaloUserId(@PathVariable String zaloUserId) {
        Optional<Customer> customer = customerService.findByZaloUserId(zaloUserId);
        if (customer.isPresent()) {
            return ResponseEntity.ok(ApiResponse.success(customer.get()));
        }
        return ResponseEntity.notFound().build();
    }

    @GetMapping("/phone/{phoneNumber}")
    public ResponseEntity<ApiResponse<Customer>> getCustomerByPhoneNumber(@PathVariable String phoneNumber) {
        Optional<Customer> customer = customerService.findByPhoneNumber(phoneNumber);
        if (customer.isPresent()) {
            return ResponseEntity.ok(ApiResponse.success(customer.get()));
        }
        return ResponseEntity.notFound().build();
    }

    @PostMapping("/search")
    public ResponseEntity<ApiResponse<List<Customer>>> searchCustomers(@RequestBody CustomerSearchRequest request) {
        List<Customer> customers = customerService.searchCustomers(request.getKeyword());
        return ResponseEntity.ok(ApiResponse.success("Found " + customers.size() + " customers", customers));
    }

    @GetMapping("/active")
    public ResponseEntity<ApiResponse<List<Customer>>> getActiveCustomers() {
        List<Customer> customers = customerService.findActiveCustomers();
        return ResponseEntity.ok(ApiResponse.success(customers));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<Customer>> createCustomer(@RequestBody Customer customer) {
        try {
            Customer createdCustomer = customerService.createCustomer(customer);
            return ResponseEntity.ok(ApiResponse.success("Customer created successfully", createdCustomer));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ApiResponse.error("Failed to create customer: " + e.getMessage()));
        }
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<Customer>> updateCustomer(@PathVariable Long id, @RequestBody Customer customer) {
        Optional<Customer> existingCustomer = customerService.findById(id);
        if (existingCustomer.isPresent()) {
            customer.setId(id);
            Customer updatedCustomer = customerService.updateCustomer(customer);
            return ResponseEntity.ok(ApiResponse.success("Customer updated successfully", updatedCustomer));
        }
        return ResponseEntity.notFound().build();
    }

    @PutMapping("/{id}/purchase")
    public ResponseEntity<ApiResponse<String>> updatePurchaseStats(@PathVariable Long id,
                                                                 @RequestParam Double amount) {
        try {
            customerService.updatePurchaseStats(id, amount);
            return ResponseEntity.ok(ApiResponse.success("Purchase stats updated successfully"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ApiResponse.error("Failed to update purchase stats: " + e.getMessage()));
        }
    }

    @PutMapping("/{id}/deactivate")
    public ResponseEntity<ApiResponse<String>> deactivateCustomer(@PathVariable Long id) {
        try {
            customerService.deactivateCustomer(id);
            return ResponseEntity.ok(ApiResponse.success("Customer deactivated successfully"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ApiResponse.error("Failed to deactivate customer: " + e.getMessage()));
        }
    }

    @GetMapping("/by-minimum-purchase")
    public ResponseEntity<ApiResponse<List<Customer>>> getCustomersByMinimumPurchase(@RequestParam Double minAmount) {
        List<Customer> customers = customerService.findCustomersByMinimumPurchase(minAmount);
        return ResponseEntity.ok(ApiResponse.success(customers));
    }
}