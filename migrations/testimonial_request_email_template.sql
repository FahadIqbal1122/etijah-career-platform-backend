insert into email_templates (key, name, description, is_active, subject_en, subject_ar, body_html_en, body_html_ar, variables) values
('testimonial_request', 'Beta Testimonial Request', 'One-off email to everyone who completed the Etijahi assessment during beta, asking for a short written testimonial ahead of the next stage. English body sent to locale=en responses, Arabic body sent to locale=ar responses.', true,
 'We''d Love to Hear Your Etijahi Experience',
 'نود أن نسمع عن تجربتك مع إتجاهي',
'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background: rgb(235, 243, 255); margin: 0px; padding: 0px; text-size-adjust: 100%;">
  <tbody><tr>
    <td align="center" style="padding: 24px 10px; text-size-adjust: 100%;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%; background: rgb(255, 255, 255); border-radius: 18px; overflow: hidden; box-shadow: rgba(0, 82, 204, 0.1) 0px 12px 40px; text-size-adjust: 100%;">

        <tbody><tr>
          <td bgcolor="#FFFFFF" style="background: rgb(255, 255, 255); padding: 38px 40px 30px; text-size-adjust: 100%;" align="center">
            <img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-logo-horizontal-single-icon.png" width="300" alt="Etijahi" style="display: block; width: 300px; max-width: 78%; height: auto; margin: 0px auto 12px; border: 0px; outline: none; text-decoration: none;">
            <p style="margin: 0px; color: rgb(90, 106, 133);"><span style="font-family: Arial, Helvetica, sans-serif; font-size: 10px;">by Etijah Coaching &amp; Consulting</span></p>
          </td>
        </tr>

        <tr>
          <td bgcolor="#0052CC" style="background: rgb(0, 82, 204); padding: 14px 40px; text-size-adjust: 100%;">
            <p style="margin: 0px; font-family: Arial, Helvetica, sans-serif; font-size: 13px; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; color: rgb(255, 255, 255); text-size-adjust: 100%;">Beta feedback · Testimonial request</p>
          </td>
        </tr>
        <tr><td style="height: 4px; background: rgb(0, 201, 167); font-size: 0px; line-height: 0; text-size-adjust: 100%;">&nbsp;</td></tr>

        <tr>
          <td dir="ltr" align="left" style="padding: 34px 40px 0px; font-family: Arial, Helvetica, sans-serif; text-size-adjust: 100%;">
            <p style="margin: 0px 0px 22px; font-family: Arial, Helvetica, sans-serif; font-size: 26px; line-height: 1.35; font-weight: bold; color: rgb(0, 82, 204);">We&rsquo;d Love to Hear Your Etijahi Experience</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">Dear {{full_name}},</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">Thank you for taking the time to complete the Etijahi assessment during our beta testing phase. We hope you found the experience useful and insightful.</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">As we prepare for the next stage of Etijahi, we would love to hear about your experience through a short written testimonial. Your feedback will help us improve the assessment and help others understand what they can expect from the experience.</p>
            <p style="margin: 0px 0px 22px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">You can write your testimonial in Arabic or English, and it can be as short as a few sentences. Feel free to share what you found useful, interesting, or different about Etijahi.</p>
          </td>
        </tr>

        <tr><td dir="ltr" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" bgcolor="#EBF3FF" style="background: rgb(235, 243, 255); border: 1px solid rgb(207, 224, 251); border-radius: 14px; padding: 28px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 20px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">Simply reply to this email with your testimonial, or send it to info@myetijahi.com.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius: 40px; text-size-adjust: 100%;">
                  <a href="mailto:info@myetijahi.com?subject=My%20Etijahi%20Testimonial" style="display: inline-block; font-family: Arial, Helvetica, sans-serif; font-size: 17px; font-weight: bold; color: rgb(255, 255, 255); text-decoration: none; padding: 17px 44px; border-radius: 40px;">Share Your Testimonial &nbsp;&rarr;</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="ltr" align="left" style="padding: 22px 40px 28px; font-family: Arial, Helvetica, sans-serif; text-size-adjust: 100%;">
          <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">Thank you again for being part of our beta testing phase and helping us shape Etijahi.</p>
          <p style="margin: 0px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">Warm regards,<br><strong>Team Etijahi</strong></p>
        </td></tr>

        <tr><td style="padding: 0px 40px 30px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td style="background: rgb(245, 249, 255); border-top: 3px solid rgb(0, 82, 204); border-radius: 14px; padding: 24px 24px 18px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 16px; font-family: Arial, Helvetica, sans-serif; font-size: 13px; line-height: 1.9; color: rgb(90, 106, 133);">Questions? Just reply to this email, or reach us on WhatsApp or by phone.</p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" style="text-size-adjust: 100%;"><tbody><tr>
                <td width="50%" align="center" valign="top" style="padding: 0px 8px 0px 0px; text-size-adjust: 100%;">
                  <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 11px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; color: rgb(90, 106, 133);">Saudi Arabia</p>
                  <p style="margin: 0px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 2.1;"><a dir="ltr" href="https://wa.me/966550770711" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">+966 55 077 0711</a></p>
                </td>
                <td width="50%" align="center" valign="top" style="padding: 0px 0px 0px 8px; text-size-adjust: 100%;">
                  <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 11px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; color: rgb(90, 106, 133);">Bahrain</p>
                  <p style="margin: 0px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 2.1;"><a dir="ltr" href="https://wa.me/97333462820" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">+973 3346 2820</a></p>
                </td>
              </tr></tbody></table>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top: 16px; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" style="border-top: 1px solid rgb(220, 231, 251); padding-top: 14px; font-family: Arial, Helvetica, sans-serif; font-size: 13px; line-height: 2.1; text-size-adjust: 100%;">
                  <a dir="ltr" href="mailto:info@myetijahi.com" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-email.png" width="16" height="16" alt="Email" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">info@myetijahi.com</a>&nbsp;&nbsp;&nbsp;&nbsp;<a dir="ltr" href="https://etijahcoaching.com/" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-website.png" width="16" height="16" alt="Website" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">etijahcoaching.com</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr>
          <td bgcolor="#00C9A7" style="background: rgb(0, 201, 167); padding: 26px 40px; text-size-adjust: 100%;" align="center">
            <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 12px; line-height: 1.6; color: rgb(255, 255, 255); font-weight: bold;">Etijah Coaching &amp; Consulting</p>
            <p style="margin: 0px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 12px; line-height: 1.6; color: rgb(255, 255, 255);">اتجاه للإرشاد والاستشارات</p>
          </td>
        </tr>

      </tbody></table>
    </td>
  </tr>
</tbody></table>',
'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background: rgb(235, 243, 255); margin: 0px; padding: 0px; text-size-adjust: 100%;">
  <tbody><tr>
    <td align="center" style="padding: 24px 10px; text-size-adjust: 100%;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%; background: rgb(255, 255, 255); border-radius: 18px; overflow: hidden; box-shadow: rgba(0, 82, 204, 0.1) 0px 12px 40px; text-size-adjust: 100%;">

        <tbody><tr>
          <td bgcolor="#FFFFFF" style="background: rgb(255, 255, 255); padding: 38px 40px 30px; text-size-adjust: 100%;" align="center">
            <img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-logo-horizontal-single-icon.png" width="300" alt="إتجاهي" style="display: block; width: 300px; max-width: 78%; height: auto; margin: 0px auto 12px; border: 0px; outline: none; text-decoration: none;">
            <p style="margin: 0px; color: rgb(90, 106, 133);"><span style="font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 10px;">من اتجاه للإرشاد والاستشارات</span></p>
          </td>
        </tr>

        <tr>
          <td bgcolor="#0052CC" style="background: rgb(0, 82, 204); padding: 14px 40px; text-size-adjust: 100%;">
            <p dir="rtl" style="margin: 0px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 15px; font-weight: bold; color: rgb(255, 255, 255); text-size-adjust: 100%;">ملاحظات المرحلة التجريبية · طلب شهادة تجربة</p>
          </td>
        </tr>
        <tr><td style="height: 4px; background: rgb(0, 201, 167); font-size: 0px; line-height: 0; text-size-adjust: 100%;">&nbsp;</td></tr>

        <tr>
          <td dir="rtl" align="right" style="padding: 34px 40px 0px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; text-size-adjust: 100%;">
            <p style="margin: 0px 0px 22px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 26px; line-height: 1.5; font-weight: bold; color: rgb(0, 82, 204);">نود أن نسمع عن تجربتك مع إتجاهي</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">عزيزي/عزيزتي {{full_name}}،</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">شكرًا لك على تخصيص وقتك لإكمال تقييم إتجاهي خلال مرحلة الاختبار التجريبي. نأمل أن تكون التجربة مفيدة ومثرية لك.</p>
            <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">ومع استعدادنا للمرحلة القادمة من إتجاهي، يسعدنا أن تشاركنا ملاحظاتك وانطباعاتك عن التجربة من خلال شهادة قصيرة مكتوبة. ستساعدنا مشاركتك في تطوير إتجاهي، كما ستساهم في تعريف الآخرين بتجربة التقييم.</p>
            <p style="margin: 0px 0px 22px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">يمكنك مشاركتنا بضع جمل قصيرة، وباللغة العربية أو الإنجليزية، حول تجربتك وما وجدته مفيدًا أو ممتعًا أو مختلفًا في إتجاهي.</p>
          </td>
        </tr>

        <tr><td dir="rtl" style="padding: 0px 40px 8px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td align="center" bgcolor="#EBF3FF" style="background: rgb(235, 243, 255); border: 1px solid rgb(207, 224, 251); border-radius: 14px; padding: 28px 26px; text-size-adjust: 100%;">
              <p style="margin: 0px 0px 20px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 14px; line-height: 1.7; color: rgb(90, 106, 133);">يمكنك ببساطة الرد على هذا البريد الإلكتروني بشهادتك، أو إرسالها إلى info@myetijahi.com.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: auto; margin: 0px auto; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" bgcolor="#00C9A7" style="border-radius: 40px; text-size-adjust: 100%;">
                  <a href="mailto:info@myetijahi.com?subject=%D8%B4%D9%87%D8%A7%D8%AF%D8%AA%D9%8A%20%D9%85%D8%B9%20%D8%A5%D8%AA%D8%AC%D8%A7%D9%87%D9%8A" style="display: inline-block; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 17px; font-weight: bold; color: rgb(255, 255, 255); text-decoration: none; padding: 17px 46px; border-radius: 40px;">‏شاركنا شهادتك&nbsp;←</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr><td dir="rtl" align="right" style="padding: 22px 40px 28px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; text-size-adjust: 100%;">
          <p style="margin: 0px 0px 16px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">شكرًا مرة أخرى لكونك جزءًا من مرحلة الاختبار التجريبي ومساهمتك في تطوير إتجاهي.</p>
          <p style="margin: 0px; font-size: 15px; line-height: 1.9; color: rgb(45, 45, 45);">مع خالص التحية،<br><strong>فريق إتجاهي</strong></p>
        </td></tr>

        <tr><td style="padding: 0px 40px 30px; text-size-adjust: 100%;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="text-size-adjust: 100%;"><tbody><tr>
            <td style="background: rgb(245, 249, 255); border-top: 3px solid rgb(0, 82, 204); border-radius: 14px; padding: 24px 24px 18px; text-size-adjust: 100%;">
              <p dir="rtl" style="margin: 0px 0px 16px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 13px; line-height: 1.9; color: rgb(90, 106, 133);">لأي سؤال: يكفي الرد على هذه الرسالة، أو تواصل معنا عبر واتساب أو الهاتف.</p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="ltr" style="text-size-adjust: 100%;"><tbody><tr>
                <td width="50%" align="center" valign="top" style="padding: 0px 8px 0px 0px; text-size-adjust: 100%;">
                  <p dir="rtl" style="margin: 0px 0px 4px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 11px; font-weight: bold; color: rgb(90, 106, 133);">السعودية</p>
                  <p style="margin: 0px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 2.1;"><a dir="ltr" href="https://wa.me/966550770711" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">+966 55 077 0711</a></p>
                </td>
                <td width="50%" align="center" valign="top" style="padding: 0px 0px 0px 8px; text-size-adjust: 100%;">
                  <p dir="rtl" style="margin: 0px 0px 4px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 11px; font-weight: bold; color: rgb(90, 106, 133);">البحرين</p>
                  <p style="margin: 0px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 2.1;"><a dir="ltr" href="https://wa.me/97333462820" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-whatsapp.png" width="16" height="16" alt="WhatsApp" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">+973 3346 2820</a></p>
                </td>
              </tr></tbody></table>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top: 16px; text-size-adjust: 100%;"><tbody><tr>
                <td align="center" style="border-top: 1px solid rgb(220, 231, 251); padding-top: 14px; font-family: Arial, Helvetica, sans-serif; font-size: 13px; line-height: 2.1; text-size-adjust: 100%;">
                  <a dir="ltr" href="mailto:info@myetijahi.com" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-email.png" width="16" height="16" alt="Email" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">info@myetijahi.com</a>&nbsp;&nbsp;&nbsp;&nbsp;<a dir="ltr" href="https://etijahcoaching.com/" style="color: rgb(0, 82, 204); text-decoration: none; font-weight: bold; white-space: nowrap;"><img src="https://erp.etijahcoaching.com/media/Etijahi/etijahi-icon-website.png" width="16" height="16" alt="Website" style="width: 16px; height: 16px; vertical-align: middle; margin: 0px 6px 3px 0px; border: 0px; outline: none; text-decoration: none;">etijahcoaching.com</a>
                </td>
              </tr></tbody></table>
            </td>
          </tr></tbody></table>
        </td></tr>

        <tr>
          <td bgcolor="#00C9A7" style="background: rgb(0, 201, 167); padding: 26px 40px; text-size-adjust: 100%;" align="center">
            <p style="margin: 0px 0px 4px; font-family: Arial, Helvetica, sans-serif; font-size: 12px; line-height: 1.6; color: rgb(255, 255, 255); font-weight: bold;">Etijah Coaching &amp; Consulting</p>
            <p style="margin: 0px; font-family: &quot;Segoe UI&quot;, Tahoma, Arial, sans-serif; font-size: 12px; line-height: 1.6; color: rgb(255, 255, 255);">اتجاه للإرشاد والاستشارات</p>
          </td>
        </tr>

      </tbody></table>
    </td>
  </tr>
</tbody></table>',
 '["full_name"]'::jsonb
)
on conflict (key) do nothing;
