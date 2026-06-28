# Internal Purchase Request Management

## Overview

This project is a custom application built on the Frappe/ERPNext framework to manage internal purchase requests. It enables employees to raise requests, managers to review and approve or reject them, and automates the creation of Material Requests upon approval.

---

## Objective

To design and implement a structured purchase request system with validation, approval workflow, and ERPNext integration.

---

## Features Implemented

### 1. Custom App

A dedicated Frappe app was created to encapsulate all functionality related to internal purchase management.

---

### 2. DocTypes

#### Internal Purchase Request

Fields implemented:

* employee
* department
* required_by_date
* status
* approval_remarks
* material_request (Link to Material Request)
* items (Child Table)

#### Internal Purchase Request Item (Child Table)

Fields implemented:

* item_code
* item_name
* quantity (qty)
* estimated_rate
* amount

---

### 3. Status Flow

The system supports the following statuses:

* Draft
* Pending
* Approval
* Approved
* Rejected
* Converted

On submission, status is automatically set to **Pending**.

---

### 4. Server-Side Validations

The following validations are implemented in the backend:

* Required date cannot be in the past
* Quantity must be greater than 0
* Estimated rate must be greater than 0
* Amount is calculated as:

  ```
  amount = quantity × estimated_rate
  ```
* Approval remarks are mandatory when status is **Rejected**

---

### 5. Client-Side Behaviour

* Amount is automatically recalculated when:

  * Quantity changes
  * Estimated rate changes
* Approval remarks field is shown only when status is **Rejected**
* "Create Material Request" button is visible only when status is **Approved**

---

### 6. Approval Actions

Custom functionality is provided to:

* Approve a request
* Reject a request (remarks required)

A whitelisted backend method is used:

```python
@frappe.whitelist()
def update_status(name, status, remarks="")
```

This method:

* Updates the status
* Validates allowed values
* Stores approval remarks

---

### 7. ERPNext Integration

For approved requests:

* A Material Request is created programmatically
* Items are mapped from Internal Purchase Request
* Material Request type is set to **Purchase**
* Schedule date is derived from required_by_date
* The created Material Request is linked back to the original document
* Status is updated to **Converted**

---

### 8. Workspace & Reports

#### Workspace

A custom workspace is created under the Public category to organize:

* Masters
* Transactions (Internal Purchase Requests)
* Reports

#### Report

A report is implemented for tracking Internal Purchase Requests with filters such as:

* Status
* Employee
* Department
* Date range

---

### 9. Permissions

* **Employee**

  * Can create, submit, and view their own requests

* **Manager**

  * Can view, approve, and reject requests

* **System Manager**

  * Full access to all records

---

## Installation

```bash
bench get-app internal_purchase [repository-link]
bench --site [site-name] install-app internal_purchase
bench migrate
```

---

## Usage

1. Employee creates and submits an Internal Purchase Request
2. Status changes to Pending
3. Manager reviews the request:

   * Approves or rejects (remarks required for rejection)
4. If approved:

   * "Create Material Request" action becomes available
   * System generates a Material Request
   * Status updates to Converted




## Future Enhancements

* Implementation of Frappe Workflow for multi-level approvals
* Email notifications on status changes
* Budget validation before approval
* Dashboard for analytics and tracking
* Role-based notification system

---

## Author

Shivaan Sharma
