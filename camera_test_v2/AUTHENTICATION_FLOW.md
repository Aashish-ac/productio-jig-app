# Authentication Flow Documentation

## Current Issues Identified

### 1. Login Logic Problems
- ❌ **No password verification**: Login window doesn't verify password against database
- ❌ **No password field**: Login window only has Employee ID and Name, no password input
- ❌ **No database lookup**: Login just accepts any credentials without checking database
- ❌ **No authentication method**: No `authenticate_user` method in database

### 2. Missing Features
- ❌ **Auto ID generation**: Admin should generate unique employee IDs automatically
- ❌ **Password policy**: User password should be `employee_id + name` automatically
- ❌ **Admin creation**: No initial admin account setup process
- ❌ **Admin ID display**: Admin dashboard doesn't show admin_id for users

## Correct Flow

### Step 1: Initial Admin Setup
1. **First time setup**: Create initial admin account manually or via script
2. Admin enters: Name, Password
3. System generates unique Employee ID (e.g., "ADM001")
4. Store in database with role='admin', admin_id=NULL

### Step 2: Admin Login
1. Admin enters: Employee ID, Name, Password
2. System verifies:
   - User exists in database
   - Role is 'admin'
   - Password matches (bcrypt verification)
3. If valid → Show Admin Dashboard

### Step 3: Admin Creates Users
1. Admin enters: Name only
2. System automatically:
   - Generates unique Employee ID (e.g., "USR001", "USR002", ...)
   - Sets password = `employee_id + name` (e.g., "USR001John Doe")
   - Links user to admin via admin_id
3. Admin receives: Employee ID and Name (to share with user)

### Step 4: User Login
1. User enters: Employee ID, Name
2. System automatically constructs password = `employee_id + name`
3. System verifies:
   - User exists in database
   - Role is 'user'
   - Password matches
   - User is active
4. If valid → Show Main Test Window

## Implementation Steps

### 1. Add Authentication Method to Database
```python
async def authenticate_user(self, employee_id: str, name: str, role: str) -> Optional[User]:
    """Authenticate user - password is employee_id + name for users"""
    user = await self.get_user_by_id(employee_id)
    if not user:
        return None
    
    # Construct password
    if role == "user":
        password = employee_id + name
    else:
        # Admin uses actual password stored in database
        # Need to check against provided password
        return None  # Will be handled separately
    
    # Verify password
    if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return user
    return None
```

### 2. Update Login Window
- Add password field (but auto-fill for users)
- For users: password is hidden and auto-generated from ID+Name
- For admins: password field is visible

### 3. Update Admin Dashboard
- Auto-generate employee IDs (USR001, USR002, etc.)
- Auto-set password as employee_id + name
- Display admin_id in user list
- Show full user record (ID + Name) for sharing

### 4. Add Admin Initialization
- Script or method to create first admin
- Or manual database insertion

