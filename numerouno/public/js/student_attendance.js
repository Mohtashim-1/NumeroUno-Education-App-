// Signature validation removed as per user request
// frappe.ui.form.on('Student Attendance', {
//     before_submit: function(frm) {
//         if (!frm.doc.custom_student_signature) {
//             // Play alert sound
//             const sound = new Audio('/assets/frappe/sounds/alert.mp3');
//             sound.play().catch(e => console.warn('Sound playback failed:', e));
//             // Show dialog
//             const dialog = frappe.msgprint({
//                 title: __('Signature Required'),
//                 indicator: 'red',
//                 message: `
//                     <div style="text-align:center; padding: 10px;">
//                         <img src="https://cdn-icons-png.flaticon.com/512/463/463612.png" width="60" style="margin-bottom: 10px;" />
//                         <h3 style="color:#d9534f;">Signature Missing</h3>
//                         <p style="font-size:14px;">Please provide your signature in the <b>Signature</b> field before submitting the attendance.</p>
//                     </div>
//                 `,
//                 primary_action: {
//                     label: __('OK'),
//                     action(dialogRef) {
//                         dialogRef.hide();
//                     }
//                 }
//             });
//             // Prevent submission
//             frappe.validated = false;
//         }
//     }
// });

// helper to make ArrayBuffer → base64
function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let b of bytes) binary += String.fromCharCode(b);
    return btoa(binary);
  }
  
  frappe.ui.form.on('Student Attendance', {
    refresh(frm) {
      frm.add_custom_button(__('Scan Fingerprint'), () => {
        requestFingerprint(frm);
      });
    }
  });
  
  async function registerFingerprint(frm) {
    // 1) get challenge
    let r1 = await frappe.call({
      method: 'numerouno.numerouno.doctype.student_attendance.student_attendance.get_challenge'
    });
    const b64 = r1.message;
    const challenge = Uint8Array.from(atob(b64), c=>c.charCodeAt(0));
  
    // 2) create credential
    const publicKey = {
      challenge,
      rp: { name: 'ERPNext' },
      user: {
        id: new TextEncoder().encode(frm.doc.name),
        name: "EDU-STU-2025-00012",
        displayName:"EDU-STU-2025-00012"
      },
      pubKeyCredParams: [{ type:'public-key', alg:-7 }],
      timeout:60000,
      userVerification:'required'
    };
  
    try {
      const cred = await navigator.credentials.create({ publicKey });
  
      // 3) manually build JSONable object
      const registration = {
        id: cred.id,
        rawId: arrayBufferToBase64(cred.rawId),
        type: cred.type,
        response: {
          attestationObject: arrayBufferToBase64(cred.response.attestationObject),
          clientDataJSON:   arrayBufferToBase64(cred.response.clientDataJSON)
        }
      };
  
      // 4) send to backend
      let r2 = await frappe.call({
        method: 'numerouno.numerouno.doctype.student_attendance.student_attendance.register_fingerprint',
        args: { credential_data: registration }
      });
  
      frappe.msgprint(r2.message);
      if (r2.credential_id) {
        localStorage.setItem('credential_id', r2.credential_id);
      }
    } catch (e) {
      frappe.msgprint(__('Registration failed: ') + e.message);
    }
  }
  
  async function requestFingerprint(frm) {
    let stored = localStorage.getItem('credential_id');
    if (!stored) {
      if (confirm(__('Fingerprint not registered. Register now?'))) {
        await registerFingerprint(frm);
        stored = localStorage.getItem('credential_id');
      }
      if (!stored) {
        frappe.msgprint(__('Registration required.'));
        return;
      }
    }
  
    // get new challenge
    let r1 = await frappe.call({
      method: 'numerouno.numerouno.doctype.student_attendance.student_attendance.get_challenge'
    });
    const bin = Uint8Array.from(atob(r1.message), c=>c.charCodeAt(0));
  
    const publicKey = {
      challenge: bin,
      allowCredentials: [{
        id: Uint8Array.from(atob(stored), c=>c.charCodeAt(0)),
        type: 'public-key'
      }],
      timeout:60000,
      userVerification:'required'
    };
  
    try {
      const assertion = await navigator.credentials.get({ publicKey });
      // package just like registration
      const authn = {
        id: assertion.id,
        rawId: arrayBufferToBase64(assertion.rawId),
        type: assertion.type,
        response: {
          authenticatorData: arrayBufferToBase64(assertion.response.authenticatorData),
          clientDataJSON:    arrayBufferToBase64(assertion.response.clientDataJSON),
          signature:         arrayBufferToBase64(assertion.response.signature),
          userHandle: assertion.response.userHandle
            ? arrayBufferToBase64(assertion.response.userHandle)
            : null
        }
      };
  
      let r2 = await frappe.call({
        method: 'numerouno.numerouno.doctype.student_attendance.student_attendance.register_fingerprint',
        args: { credential_data: registration }
      });
  
      frappe.msgprint(r2.message);
      if (r2.message.includes('Attendance marked')) {
        frm.reload_doc();
      }
    } catch (e) {
      frappe.msgprint(__('Fingerprint scan failed: ') + e.message);
    }
  }