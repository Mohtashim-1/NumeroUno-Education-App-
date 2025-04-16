frappe.ui.form.on('Student Attendance', {
    before_submit: function(frm) {
        if (!frm.doc.custom_student_signature) {

            // Play alert sound
            const sound = new Audio('/assets/frappe/sounds/alert.mp3');
            sound.play().catch(e => console.warn('Sound playback failed:', e));

            // Show dialog
            const dialog = frappe.msgprint({
                title: __('Signature Required'),
                indicator: 'red',
                message: `
                    <div style="text-align:center; padding: 10px;">
                        <img src="https://cdn-icons-png.flaticon.com/512/463/463612.png" width="60" style="margin-bottom: 10px;" />
                        <h3 style="color:#d9534f;">Signature Missing</h3>
                        <p style="font-size:14px;">Please provide your signature in the <b>Signature</b> field before submitting the attendance.</p>
                    </div>
                `,
                primary_action: {
                    label: __('OK'),
                    action(dialogRef) {
                        dialogRef.hide();
                    }
                }
            });

            // Prevent submission
            frappe.validated = false;
        }
    }
});
