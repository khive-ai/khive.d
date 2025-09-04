// @ts-nocheck
"use client";

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  TextField,
  Chip,
  Grid,
  Tabs,
  Tab,
  InputAdornment,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import {
  ExpandMore,
  Search,
  Person,
  Domain,
  Code,
  Psychology,
  TrendingUp,
  Speed,
  Build,
  Visibility,
  Category
} from '@mui/icons-material';
import { useRoles, useDomains } from '../../../lib/services/agent-composition';
import { Role, Domain } from '../../../lib/types/agent-composition';

interface RoleDomainBrowserProps {
  onRoleSelect?: (role: Role) => void;
  onDomainSelect?: (domain: Domain) => void;
  selectedRole?: Role | null;
  selectedDomain?: Domain | null;
}

export function RoleDomainBrowser({ 
  onRoleSelect, 
  onDomainSelect,
  selectedRole,
  selectedDomain 
}: RoleDomainBrowserProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [detailDialog, setDetailDialog] = useState<{ type: 'role' | 'domain'; item: Role | Domain } | null>(null);

  const { data: roles, isLoading: rolesLoading } = useRoles();
  const { data: domains, isLoading: domainsLoading } = useDomains();

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const filteredRoles = roles?.filter(role => 
    role.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    role.purpose.toLowerCase().includes(searchTerm.toLowerCase()) ||
    role.core_actions.some(action => action.toLowerCase().includes(searchTerm.toLowerCase()))
  ) || [];

  const filteredDomains = domains?.filter(domain =>
    domain.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    domain.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
    domain.metrics.some(metric => metric.toLowerCase().includes(searchTerm.toLowerCase()))
  ) || [];

  const handleViewDetails = (type: 'role' | 'domain', item: Role | Domain) => {
    setDetailDialog({ type, item });
  };

  const handleCloseDetails = () => {
    setDetailDialog(null);
  };

  const renderRoleCard = (role: Role) => (
    <Card 
      key={role.id}
      sx={{ 
        cursor: 'pointer',
        border: selectedRole?.id === role.id ? 2 : 1,
        borderColor: selectedRole?.id === role.id ? 'primary.main' : 'divider',
        '&:hover': { borderColor: 'primary.light' }
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Person sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6">{role.id}</Typography>
          </Box>
          <Button
            size="small"
            onClick={() => handleViewDetails('role', role)}
            startIcon={<Visibility />}
          >
            Details
          </Button>
        </Box>
        
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {role.purpose.slice(0, 100)}...
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Core Actions</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {role.core_actions.map(action => (
              <Chip key={action} label={action} size="small" variant="outlined" />
            ))}
          </Box>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Tools</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {role.tools.slice(0, 3).map(tool => (
              <Chip key={tool} label={tool} size="small" />
            ))}
            {role.tools.length > 3 && (
              <Chip label={`+${role.tools.length - 3}`} size="small" />
            )}
          </Box>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            {role.kpis.length} KPIs • Hands off to {role.handoff_to.length} roles
          </Typography>
          <Button
            size="small"
            variant="contained"
            onClick={() => onRoleSelect?.(role)}
            disabled={selectedRole?.id === role.id}
          >
            {selectedRole?.id === role.id ? 'Selected' : 'Select'}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );

  const renderDomainCard = (domain: Domain) => (
    <Card 
      key={domain.id}
      sx={{ 
        cursor: 'pointer',
        border: selectedDomain?.id === domain.id ? 2 : 1,
        borderColor: selectedDomain?.id === domain.id ? 'secondary.main' : 'divider',
        '&:hover': { borderColor: 'secondary.light' }
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Domain sx={{ mr: 1, color: 'secondary.main' }} />
            <Typography variant="h6">{domain.id}</Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip label={domain.type} size="small" />
            <Button
              size="small"
              onClick={() => handleViewDetails('domain', domain)}
              startIcon={<Visibility />}
            >
              Details
            </Button>
          </Box>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Knowledge Patterns</Typography>
          <Typography variant="body2" color="text.secondary">
            {Object.keys(domain.knowledge_patterns).length} pattern categories
          </Typography>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Specialized Tools</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {Object.keys(domain.specialized_tools).slice(0, 3).map(tool => (
              <Chip key={tool} label={tool.replace('_', ' ')} size="small" variant="outlined" />
            ))}
            {Object.keys(domain.specialized_tools).length > 3 && (
              <Chip label={`+${Object.keys(domain.specialized_tools).length - 3}`} size="small" />
            )}
          </Box>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            {domain.metrics.length} metrics • {Object.keys(domain.best_practices).length} best practices
          </Typography>
          <Button
            size="small"
            variant="contained"
            color="secondary"
            onClick={() => onDomainSelect?.(domain)}
            disabled={selectedDomain?.id === domain.id}
          >
            {selectedDomain?.id === domain.id ? 'Selected' : 'Select'}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );

  const renderRoleDetails = (role: Role) => (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Person sx={{ mr: 1, color: 'primary.main', fontSize: 32 }} />
        <Box>
          <Typography variant="h5">{role.id}</Typography>
          <Typography variant="body2" color="text.secondary">{role.purpose}</Typography>
        </Box>
      </Box>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Build sx={{ mr: 1 }} />
          <Typography>Core Actions & Tools</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Typography variant="subtitle2" gutterBottom>Core Actions</Typography>
              <List dense>
                {role.core_actions.map(action => (
                  <ListItem key={action}>
                    <ListItemText primary={action} />
                  </ListItem>
                ))}
              </List>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="subtitle2" gutterBottom>Available Tools</Typography>
              <List dense>
                {role.tools.map(tool => (
                  <ListItem key={tool}>
                    <ListItemText primary={tool} />
                  </ListItem>
                ))}
              </List>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Category sx={{ mr: 1 }} />
          <Typography>Inputs & Outputs</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Typography variant="subtitle2" gutterBottom>Expected Inputs</Typography>
              <List dense>
                {role.inputs.map(input => (
                  <ListItem key={input}>
                    <ListItemText primary={input} />
                  </ListItem>
                ))}
              </List>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="subtitle2" gutterBottom>Deliverables</Typography>
              <List dense>
                {role.outputs.map(output => (
                  <ListItem key={output}>
                    <ListItemText primary={output} />
                  </ListItem>
                ))}
              </List>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <TrendingUp sx={{ mr: 1 }} />
          <Typography>Performance & Authority</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle2" gutterBottom>Key Performance Indicators</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
            {role.kpis.map(kpi => (
              <Chip key={kpi} label={kpi} size="small" />
            ))}
          </Box>
          
          <Typography variant="subtitle2" gutterBottom>Authority</Typography>
          <Typography variant="body2">{role.authority}</Typography>
          
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6}>
              <Typography variant="subtitle2">Hands off to:</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {role.handoff_to.map(handoff => (
                  <Chip key={handoff} label={handoff} size="small" variant="outlined" />
                ))}
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="subtitle2">Receives from:</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {role.handoff_from.length > 0 ? (
                  role.handoff_from.map(handoff => (
                    <Chip key={handoff} label={handoff} size="small" variant="outlined" />
                  ))
                ) : (
                  <Typography variant="caption" color="text.secondary">No incoming handoffs</Typography>
                )}
              </Box>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
    </Box>
  );

  const renderDomainDetails = (domain: Domain) => (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Domain sx={{ mr: 1, color: 'secondary.main', fontSize: 32 }} />
        <Box>
          <Typography variant="h5">{domain.id}</Typography>
          <Chip label={domain.type} size="small" />
        </Box>
      </Box>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Psychology sx={{ mr: 1 }} />
          <Typography>Knowledge Patterns</Typography>
        </AccordionSummary>
        <AccordionDetails>
          {Object.entries(domain.knowledge_patterns).map(([category, patterns]) => (
            <Box key={category} sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                {category.replace('_', ' ').toUpperCase()}
              </Typography>
              {Array.isArray(patterns) ? (
                <List dense>
                  {patterns.map((pattern: any, index: number) => (
                    <ListItem key={index}>
                      <ListItemText 
                        primary={pattern.pattern || `Pattern ${index + 1}`}
                        secondary={pattern.characteristics?.join(', ') || JSON.stringify(pattern)}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  {JSON.stringify(patterns, null, 2)}
                </Typography>
              )}
            </Box>
          ))}
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Build sx={{ mr: 1 }} />
          <Typography>Specialized Tools</Typography>
        </AccordionSummary>
        <AccordionDetails>
          {Object.entries(domain.specialized_tools).map(([category, tools]) => (
            <Box key={category} sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                {category.replace('_', ' ').toUpperCase()}
              </Typography>
              {Array.isArray(tools) ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {tools.map((tool: string) => (
                    <Chip key={tool} label={tool} size="small" variant="outlined" />
                  ))}
                </Box>
              ) : (
                <Typography variant="body2">{JSON.stringify(tools)}</Typography>
              )}
            </Box>
          ))}
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Speed sx={{ mr: 1 }} />
          <Typography>Metrics & Best Practices</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>Key Metrics</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {domain.metrics.map(metric => (
                <Chip key={metric} label={metric} size="small" />
              ))}
            </Box>
          </Box>

          <Typography variant="subtitle2" gutterBottom>Best Practices</Typography>
          {Object.entries(domain.best_practices).map(([category, practices]) => (
            <Box key={category} sx={{ mb: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                {category.replace('_', ' ')}:
              </Typography>
              {Array.isArray(practices) ? (
                <List dense>
                  {practices.map((practice: string, index: number) => (
                    <ListItem key={index} sx={{ pl: 2 }}>
                      <ListItemText 
                        primary={practice}
                        primaryTypographyProps={{ variant: 'caption' }}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="caption" color="text.secondary">
                  {JSON.stringify(practices)}
                </Typography>
              )}
            </Box>
          ))}
        </AccordionDetails>
      </Accordion>
    </Box>
  );

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Paper sx={{ p: 2, borderRadius: 0 }}>
        <Typography variant="h6" gutterBottom>
          Role & Domain Browser
        </Typography>
        <TextField
          fullWidth
          placeholder="Search roles and domains..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
          size="small"
        />
      </Paper>

      <Paper sx={{ borderRadius: 0 }}>
        <Tabs value={activeTab} onChange={handleTabChange} centered>
          <Tab 
            label={`Roles (${filteredRoles.length})`}
            icon={<Person />}
          />
          <Tab 
            label={`Domains (${filteredDomains.length})`}
            icon={<Domain />}
          />
        </Tabs>
      </Paper>

      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {activeTab === 0 && (
          <Grid container spacing={2}>
            {filteredRoles.map(role => (
              <Grid item xs={12} lg={6} key={role.id}>
                {renderRoleCard(role)}
              </Grid>
            ))}
          </Grid>
        )}

        {activeTab === 1 && (
          <Grid container spacing={2}>
            {filteredDomains.map(domain => (
              <Grid item xs={12} lg={6} key={domain.id}>
                {renderDomainCard(domain)}
              </Grid>
            ))}
          </Grid>
        )}
      </Box>

      <Dialog
        open={!!detailDialog}
        onClose={handleCloseDetails}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {detailDialog?.type === 'role' ? 'Role Details' : 'Domain Details'}
        </DialogTitle>
        <DialogContent>
          {detailDialog?.type === 'role' 
            ? renderRoleDetails(detailDialog.item as Role)
            : renderDomainDetails(detailDialog.item as Domain)
          }
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDetails}>Close</Button>
          <Button
            variant="contained"
            onClick={() => {
              if (detailDialog?.type === 'role') {
                onRoleSelect?.(detailDialog.item as Role);
              } else {
                onDomainSelect?.(detailDialog.item as Domain);
              }
              handleCloseDetails();
            }}
          >
            Select {detailDialog?.type === 'role' ? 'Role' : 'Domain'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}