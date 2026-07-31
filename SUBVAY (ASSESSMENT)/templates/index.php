<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="{{url_for('static', filename='styles.css')}}">
    <link rel="sylesheet"href="https://www.w3schools.com/w3css/4/w3.css">
    <title>Full-Stack Login & Register Form With User Page</title>
</head>
<body>
    
<div class="container">
    <div class="form-box active" id="login-form">
        <form action="">
            <h2>Login</h2>
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit" name="login">Login</button>
            <p>Don't have an account? <a href="#" onclick="showForm('register-form')">Register</a></p>
            </form>
        </div>
 </div>

<div class="container">
    <div class="form-box" id="register-form>
        <form action="">
            <h2>Register</h2>
            <input type="firstname" name="firstname" placeholder="First name" required>
            <input type="lastname" name="lastname" placeholder="Last name" required>
            <input type="email" name="email" placeholder="Email" required>
            <input type="phonenumber" name="phonenumber" placeholder="Phone number" required>
            <input type="password" name="password" placeholder="Password" required>
            <input type="conpassword" name="conpassword" placeholder="Confirm password" required>
            <select name="prefstore"
                <option value="">--Select Prefered Store--</option>
                <option value="176 Williams Street, Store 1">176 Williams Street, Store 1</option>
                <option value="75 Victoria Street, Store 2">75 Victoria Street, Store 2</option>
                <option value="Main North & Radcliffe Roads, Store 3">Main North & Radcliffe Roads, Store 3</option>
                <option value="60 Queens Park Drive, Store 4">60 Queens Park Drive, Store 4</option>
                <option value="322 Harewood Road, Store 5">322 Harewood Road, Store 5</option>
                <option value="481 Papanui Rd, Store 6">481 Papanui Rd, Store 6</option>
                <option value="91 Brighton Mall, Store 7">91 Brighton Mall, Store 7</option>
                <option value="202-206 Hills Rd, Store 8">202-206 Hills Rd, Store 8</option>
                <option value="530 Memorial Ave, Store 9">530 Memorial Ave, Store 9</option>
                <option value="Cnr Buckleys Rd & Linwood Ave, Store 10">Cnr Buckleys Rd & Linwood Ave, Store 10</option>
                <option value="265 Cashel St, Store 11">265 Cashel St, Store 11</option>
                <option value="555 Colombo St, Store 12">555 Colombo St, Store 12</option>
                <option value="334 Riccarton Rd, Store 13">334 Riccarton Rd, Store 13</option>
                <option value="1 Matipo St, Store 14">1 Matipo St, Store 14</option>
                <option value="330 Colombo Street, Store 15">330 Colombo Street, Store 15</option>
                <option value="1005 Ferry Road, Store 16">1005 Ferry Road, Store 16</option>
                <option value="256 Barrington Street, Store 17">256 Barrington Street, Store 17</option>
                <option value="7-11 Chalmers Street, Store 18">7-11 Chalmers Street, Store 18</option>
                <option value="118 The Runway, Store 19">118 The Runway, Store 19</option>
                <option value="1 Hamill Road, Store 20">1 Hamill Road, Store 20</option>
                <option value="70-76 Rolleston Drive, Store 21">70-76 Rolleston Drive, Store 21</option>
                <option value="5 Roberts Street, Store 22">5 Roberts Street, Store 22</option>
                <option value="188 West St, Store 23">188 West St, Store 23</option>
                <option value="78 Beach Road, Store 24">78 Beach Road, Store 24</option>
                <option value="174a Mawhera Quay, Store 25">174a Mawhera Quay, Store 25</option>
            </select>
        <select name="gender"
            <option value="">--Select Gender--</option>
            <option valie="Male">Male</option>
            <option valie="Female">Female</option>
            <option valie="Other">Other</option>
        </select>
            <button type="submit" name="Register">Register</button>
            <p>Already have an account? <a href="#" onclick="showForm('login-form')
            ">Login</a></p>
            </form>
        </div>
 </div>

    <script src="script.js"></script>

</body>
</html>