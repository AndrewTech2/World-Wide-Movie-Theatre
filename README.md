# World Wide Movie Theatre (WWMT)
The World Wide Movie Theatre is a fully functional movie reservation web system usable by viewers and administrators alike. It combines various frontend elements with quintessential backend elements such as database design and logic handling in <strong>Python</strong> and <strong>JavaScript</strong>.
<h3>Demonstration</h3>
<h1>TODO</h1>
<h3>Features</h3>
<ul>
    <li>Registration system: Users can register an user account or an administrator account. The administrator account has additional privileges, such as managing movie running time slots.</li>
    <li>Movie selection: Users can select a film to watch at a fixed point in time managed by an administrator. Subsequently, they must pick their spots (if available) and pay the sum. Users may also filter by genre.</li>
    <li>Movie time slots management: Administrators can add movie time slots, edit them or remove them.</li>
    <li>Automated user annoucements: Should a movie's details be modified, the users who have paid the full price for securing a dedicated ticket will be urgently notified by e-mail.</li>
    <li>Refund system: Users can have their sum refunded immediately.</li>  
    <li>Ticket section: The website features a dedicated section where users can view and show their tickets to staff.</li>  
</ul>
<h3>Implementation details</h3>
Several web technologies are thoroughly used to ensure proper website functionality. The front-end is managed using HTML, CSS and JavaScript (to ensure form compliance), whereas the back-end is managed primarily in Python in Flask, a dedicated micro-framework. Databases are managed using SQLITE3 in Python.

