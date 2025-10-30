# Complete Authentication System Setup Guide

## ✅ **What Has Been Fixed**

### 1. **Database Authentication Method** ✅
- Added `authenticate_user()` method to `database/models.py`
- Handles both Admin and User authentication
- **For Users**: Password = `employee_id + name` (automatic)
- **For Admins**: Requires provided password

### 2. **Login Window Updated** ✅
- Added password field (optional for users, required for admins)
- Auto-enables/disables password field based on role
- Shows help text explaining password policy
- Emits password to app.py for verification

### 3. **App.py Authentication Flow** ✅
- `on_login_attempt()` now calls database authentication
- `_authenticate_and_login()` verifies credentials with database
- Checks role matches
- Only proceeds if authentication succeeds

### 4. **Admin Dashboard User Creation** ✅
- **Auto-generates Employee ID**: USR001, USR002, etc.
- **Auto-sets Password**: `employee_id + name`
- **Readonly fields**: Employee ID and Password are readonly (auto-generated)
- **Displays Admin ID**: Shows admin_id in user list for monitoring
- **Shows credentials**: Displays Employee ID and Password after creation for sharing

### 5. **Admin Initialization Script** ✅
- Created `create_admin.py` to set up first admin account
- Generates Admin ID (ADM001, ADM002, etc.)
- Requires name and password input

---

## 📋 **Complete Setup Steps**

### **Step 1: Install Dependencies**

```bash
cd camera_test_v2
pip install -r requirements.txt
```

Required packages:
- `bcrypt>=4.0.0` (for password hashing)
- `psycopg2-binary>=2.9.0` (for PostgreSQL - synchronous driver)
- `SQLAlchemy>=2.0.0`

### **Step 2: Set Up PostgreSQL Database**

1. **Install PostgreSQL** (if not already installed)
2. **Create database**:
   ```sql
   CREATE DATABASE camera_test_db;
   CREATE USER camera_test_user WITH PASSWORD 'camera_test_pass';
   GRANT ALL PRIVILEGES ON DATABASE camera_test_db TO camera_test_user;
   ```

3. **Update `core/config.py`** if using different credentials:
   ```python
   DB_HOST = "localhost"
   DB_PORT = 5432
   DB_NAME = "camera_test_db"
   DB_USER = "camera_test_user"
   DB_PASSWORD = "camera_test_pass"
   ```

### **Step 3: Create Initial Admin Account**

Run the admin creation script:

```bash
python create_admin.py
```

**Example:**
```
Enter Admin Full Name: John Admin
Enter Admin Password: admin123

✓ Admin Account Created Successfully!
Employee ID: ADM001
Name: John Admin
Password: admin123
```

**Important**: Save these credentials - you'll need them to login!

### **Step 4: Run the Application**

```bash
python app.py
```

---

## 🔐 **Authentication Flow**

### **Admin Login**
1. Select **"Admin"** role
2. Enter **Employee ID** (e.g., "ADM001")
3. Enter **Full Name** (e.g., "John Admin")
4. Enter **Password** (the password you set when creating admin)
5. Click **Login**

**System verifies:**
- User exists in database
- Role is 'admin'
- Password matches (bcrypt verification)
- Name matches

### **Admin Creates User**
1. Admin logs in → Admin Dashboard opens
2. Click **"➕ Add User"**
3. **Enter Name only** (e.g., "Jane Tester")
4. Click **"💾 Save User"**

**System automatically:**
- Generates Employee ID (e.g., "USR001")
- Sets Password = `employee_id + name` (e.g., "USR001Jane Tester")
- Links to admin via `admin_id`
- Stores in database with bcrypt hashed password

**Admin receives popup:**
```
User created successfully!

Employee ID: USR001
Name: Jane Tester
Password: USR001Jane Tester

Share these credentials with the user.
```

### **User Login**
1. User receives credentials from admin:
   - Employee ID: `USR001`
   - Name: `Jane Tester`
   - Password: `USR001Jane Tester` (auto-generated)

2. User logs in:
   - Select **"User"** role
   - Enter **Employee ID**: `USR001`
   - Enter **Full Name**: `Jane Tester`
   - **Leave Password blank** (auto-generated from ID + Name)
   - Click **Login**

**System automatically:**
- Constructs password = `USR001` + `Jane Tester` = `USR001Jane Tester`
- Verifies against database (bcrypt)
- Checks user is active
- Checks name matches

---

## 🗄️ **Database Structure**

### **User Table Schema**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    employee_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hashed
    role VARCHAR(20) DEFAULT 'user',        -- 'user' or 'admin'
    is_active BOOLEAN DEFAULT TRUE,
    admin_id INTEGER NULL,                 -- Links user to creating admin
    created_at DATETIME DEFAULT NOW()
);
```

### **Relationships**
- **Admin → Users**: One admin can create many users (via `admin_id`)
- **User → Test Results**: One user can have many test results

---

## 📊 **Admin Dashboard Features**

### **User List Panel (Left)**
- Shows all users created by admin
- Displays: `👤 Name (Employee ID) [Admin ID: X]`
- Click user to edit/delete
- Click "➕ Add User" to create new user

### **User Management Panel (Top Right)**
- **Employee ID**: Readonly, auto-generated (USR001, USR002, ...)
- **Full Name**: Editable input
- **Password**: Readonly, shows preview: `employee_id + name`
- **Role**: Readonly, always "user"
- **Save**: Creates or updates user
- **Delete**: Soft delete (sets is_active=False)

### **Test Results Panel (Bottom Right)**
- Displays all test results from admin's users
- Filter by: User, Status (PASS/FAIL), Date
- Export to CSV
- Shows: User, Employee ID, Camera Serial, LED, IRLED, IRCUT, Speaker, Date

---

## 🔧 **Key Code Locations**

### **Authentication Logic**
- **Database method**: `database/models.py` → `authenticate_user()`
- **Login window**: `gui/login_window.py` → `handle_login()`
- **App authentication**: `app.py` → `_authenticate_and_login()`

### **User Creation Logic**
- **Auto ID generation**: `database/models.py` → `generate_next_employee_id()`
- **User creation**: `database/models.py` → `create_user()`
- **Admin UI**: `gui/admin_dashboard.py` → `_save_user_async()`

### **Password Handling**
- **Hashing**: `database/models.py` → Uses `bcrypt.hashpw()`
- **Verification**: `database/models.py` → Uses `bcrypt.checkpw()`
- **Auto-generation**: Password = `employee_id + name` (for users)

---

## ✅ **Security Features**

1. **Password Hashing**: All passwords stored as bcrypt hashes (never plaintext)
2. **Name Verification**: Login requires exact name match (case-insensitive)
3. **Role Verification**: Login verifies selected role matches database role
4. **Active Check**: Inactive users cannot login
5. **Admin Linking**: Users linked to creating admin for accountability

---

## 🚀 **Testing the System**

### **Test Admin Login**
1. Run `python create_admin.py`
2. Create admin: Name="Test Admin", Password="test123"
3. Run `python app.py`
4. Login with: ADM001, "Test Admin", "test123"

### **Test User Creation**
1. Login as admin
2. Click "➕ Add User"
3. Enter Name: "Test User"
4. Click "💾 Save User"
5. Copy credentials from popup

### **Test User Login**
1. Logout (close admin dashboard)
2. Login window appears
3. Select "User"
4. Enter Employee ID and Name (from step 5 above)
5. Leave password blank
6. Click Login

---

## 📝 **Important Notes**

1. **First Admin**: Must be created via `create_admin.py` script
2. **User Passwords**: Always `employee_id + name` (cannot be changed)
3. **Admin Passwords**: Set during admin creation, can be changed via database update
4. **Employee IDs**: Auto-generated, cannot be manually set
5. **Admin ID Display**: Shows in user list for tracking which admin created the user

---

## 🐛 **Troubleshooting**

### **"Database not available" error**
- Check PostgreSQL is running
- Verify database credentials in `core/config.py`
- Ensure database and user exist

### **"Authentication failed"**
- Verify Employee ID and Name match exactly (case-insensitive)
- For users: Password is automatic (employee_id + name)
- For admins: Verify password is correct

### **"User already exists"**
- Employee ID must be unique
- Check if user was previously created

### **Admin ID not showing**
- Verify `admin_id` is populated in database
- Check admin dashboard user list display logic

---

**System Status**: ✅ **AUTHENTICATION SYSTEM COMPLETE**

All authentication flows are now properly implemented and connected to the database!

